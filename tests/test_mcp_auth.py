"""Auth del endpoint /mcp: OAuth (GitHub) + lista blanca, montaje y fallo cerrado."""
import importlib

import pytest
from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.server.auth.redirect_validation import matches_allowed_pattern
from key_value.aio.stores.memory import MemoryStore
from starlette.testclient import TestClient

from app.mcp import build_mcp_app
from app.mcp.auth import CLAUDE_AI_CALLBACK, allowed_redirect_uris, build_auth_from_env

BASE_URL = "https://portfolio.example"
ENV = {
    "MCP_BASE_URL": BASE_URL,
    "GITHUB_CLIENT_ID": "test-client-id",
    "GITHUB_CLIENT_SECRET": "test-client-secret",
    "MCP_ALLOWED_GITHUB_USERS": "PabloVasta, otra-cuenta",
    "MCP_JWT_SIGNING_KEY": "k" * 48,
    "MONGOCLUSTER": "mongodb://localhost:27017",
}
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
TOOLS_LIST = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
INSPECTOR_CALLBACK = "http://localhost:6274/oauth/callback"


def register(client, redirect_uri):
    return client.post(
        "/register",
        json={
            "redirect_uris": [redirect_uri],
            "client_name": "test",
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        },
    )


@pytest.fixture
def fake_tokens(monkeypatch):
    """Sustituye la validación upstream: el token 'tok-<login>' es del usuario <login>."""

    async def fake_load(self, token):
        if not token.startswith("tok-"):
            return None
        login = token.removeprefix("tok-")
        return AccessToken(token=token, client_id="c", scopes=["read:user"], claims={"login": login})

    monkeypatch.setattr(OAuthProxy, "load_access_token", fake_load)


def mcp_client(env=ENV):
    app = build_mcp_app(env, client_storage=MemoryStore())
    assert app is not None
    return TestClient(app, base_url=BASE_URL)


# ------------------------------------------------------------ configuración

@pytest.mark.parametrize("missing", ["MCP_BASE_URL", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET",
                                     "MCP_ALLOWED_GITHUB_USERS", "MCP_JWT_SIGNING_KEY"])
def test_fails_closed_without_required_env(missing):
    env = {**ENV, missing: ""}
    assert build_auth_from_env(env, client_storage=MemoryStore()) is None
    assert build_mcp_app(env, client_storage=MemoryStore()) is None


def test_rejects_short_signing_key():
    assert build_auth_from_env({**ENV, "MCP_JWT_SIGNING_KEY": "corta"}, client_storage=MemoryStore()) is None


def test_rejects_blank_allowlist():
    assert build_auth_from_env({**ENV, "MCP_ALLOWED_GITHUB_USERS": " , "}, client_storage=MemoryStore()) is None


def test_redirect_uris_production_only_claude():
    for env in (ENV, {**ENV, "MCP_ENV": "production"}, {**ENV, "MCP_ENV": "dev"}):
        uris = allowed_redirect_uris(env)
        assert uris == [CLAUDE_AI_CALLBACK]
        assert not any(matches_allowed_pattern(INSPECTOR_CALLBACK, p) for p in uris)


def test_redirect_uris_development_allows_localhost():
    uris = allowed_redirect_uris({**ENV, "MCP_ENV": "Development"})
    assert CLAUDE_AI_CALLBACK in uris
    assert any(matches_allowed_pattern(INSPECTOR_CALLBACK, p) for p in uris)
    assert not any(matches_allowed_pattern("http://localhost@evil.example/cb", p) for p in uris)


# ------------------------------------------------------------ HTTP

def test_mcp_requires_token():
    with mcp_client() as client:
        resp = client.post("/mcp", json=TOOLS_LIST, headers=MCP_HEADERS)
        assert resp.status_code == 401
        assert f'resource_metadata="{BASE_URL}/.well-known/oauth-protected-resource/mcp"' in resp.headers["www-authenticate"]

        resp = client.post("/mcp", json=TOOLS_LIST, headers={**MCP_HEADERS, "Authorization": "Bearer basura"})
        assert resp.status_code == 401


def test_oauth_discovery_metadata():
    with mcp_client() as client:
        resource = client.get("/.well-known/oauth-protected-resource/mcp").json()
        assert resource["resource"] == f"{BASE_URL}/mcp"

        server = client.get("/.well-known/oauth-authorization-server").json()
        assert server["registration_endpoint"] == f"{BASE_URL}/register"
        assert server["authorization_endpoint"] == f"{BASE_URL}/authorize"
        assert server["token_endpoint"] == f"{BASE_URL}/token"


def test_dynamic_registration_redirects_production():
    with mcp_client() as client:
        assert register(client, CLAUDE_AI_CALLBACK).status_code == 201
        resp = register(client, INSPECTOR_CALLBACK)
        assert resp.status_code == 400
        assert resp.json()["error"] == "invalid_redirect_uri"
        assert register(client, "https://evil.example/callback").status_code == 400


def test_dynamic_registration_redirects_development():
    with mcp_client({**ENV, "MCP_ENV": "development"}) as client:
        assert register(client, INSPECTOR_CALLBACK).status_code == 201
        assert register(client, "https://evil.example/callback").status_code == 400


def test_allowlisted_user_can_list_tools(fake_tokens):
    with mcp_client() as client:
        # El login de GitHub se compara sin distinguir mayúsculas
        resp = client.post("/mcp", json=TOOLS_LIST, headers={**MCP_HEADERS, "Authorization": "Bearer tok-pablovasta"})
        assert resp.status_code == 200
        assert "list_projects" in resp.text


def test_non_allowlisted_user_is_rejected(fake_tokens):
    with mcp_client() as client:
        resp = client.post("/mcp", json=TOOLS_LIST, headers={**MCP_HEADERS, "Authorization": "Bearer tok-intruso"})
        assert resp.status_code == 401


# ------------------------------------------------------------ integración en app.main

@pytest.fixture
def main_with_mcp(monkeypatch):
    """Recarga app.main con la configuración OAuth presente (estado OAuth en memoria)."""
    import app.main
    import app.mcp.auth as auth_module

    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(auth_module, "_mongo_client_storage", lambda env: MemoryStore())
    module = importlib.reload(app.main)
    yield module
    monkeypatch.undo()
    importlib.reload(app.main)


def test_main_app_mounts_mcp_without_breaking_rest(main_with_mcp):
    assert main_with_mcp.mcp_app is not None
    with TestClient(main_with_mcp.app, base_url=BASE_URL, follow_redirects=False) as client:
        assert client.post("/mcp", json=TOOLS_LIST, headers=MCP_HEADERS).status_code == 401
        assert client.get("/.well-known/oauth-authorization-server").status_code == 200
        # El REST y el panel siguen igual
        assert client.get("/api/v1/projects").json() == []
        assert client.get("/").status_code == 200
        assert client.get("/login").status_code == 200
        assert client.get("/dashboard").headers["location"] == "/login"
        assert client.get("/no-existe").status_code == 404


def test_main_app_without_config_has_no_mcp():
    import app.main

    assert app.main.mcp_app is None
    with TestClient(app.main.app) as client:
        assert client.post("/mcp", json=TOOLS_LIST, headers=MCP_HEADERS).status_code == 404
        assert client.get("/.well-known/oauth-authorization-server").status_code == 404


# ------------------------------------------------------------ rotación de MCP_JWT_SIGNING_KEY

async def test_rotating_signing_key_invalidates_oauth_state():
    """El estado OAuth guardado se cifra con una clave derivada de MCP_JWT_SIGNING_KEY.

    Con la misma clave, el estado sobrevive a un reinicio; si se rota la clave, los clientes
    registrados y los tokens emitidos dejan de valer, y hay que reconectar el conector.
    """
    store = MemoryStore()  # hace de Mongo, compartido entre "reinicios"
    app = build_mcp_app(ENV, client_storage=store)
    with TestClient(app, base_url=BASE_URL) as client:
        client_id = register(client, CLAUDE_AI_CALLBACK).json()["client_id"]

    def provider(env):
        auth = build_auth_from_env(env, client_storage=store)
        auth.get_routes(mcp_path="/mcp")  # inicializa el emisor de JWT, como al montar la app
        return auth

    old = provider(ENV)
    token = old.jwt_issuer.issue_access_token(client_id=client_id, scopes=["read:user"], jti="jti-1")

    # Reinicio con la misma clave: el registro y el token siguen siendo válidos
    same = provider(ENV)
    assert await same.get_client(client_id) is not None
    assert same.jwt_issuer.verify_token(token)["client_id"] == client_id

    # Clave rotada: el registro no se puede descifrar y el token no se puede verificar
    rotated = provider({**ENV, "MCP_JWT_SIGNING_KEY": "n" * 48})
    assert await rotated.get_client(client_id) is None
    with pytest.raises(Exception):
        rotated.jwt_issuer.verify_token(token)
