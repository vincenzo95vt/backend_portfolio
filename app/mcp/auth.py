"""Autenticación OAuth del servidor MCP: GitHub + lista blanca de usuarios.

claude.ai solo admite conectores con OAuth (o sin auth), por eso se usa el
proxy OAuth de FastMCP sobre GitHub. Este proxy hace el registro dinámico de
clientes que necesita claude.ai y emite sus propios tokens JWT.

Si falta alguna variable obligatoria, ``build_auth_from_env`` devuelve None y
el servidor MCP no se monta: el fallo es cerrado, nunca queda abierto sin auth.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Mapping

from cryptography.fernet import Fernet
from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.auth.jwt_issuer import derive_jwt_key
from fastmcp.server.auth.providers.github import GitHubProvider
from key_value.aio.protocols import AsyncKeyValue
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from key_value.aio.wrappers.prefix_collections import PrefixCollectionsWrapper

logger = logging.getLogger("app.mcp.auth")

CLAUDE_AI_CALLBACK = "https://claude.ai/api/mcp/auth_callback"
DEV_REDIRECT_URIS = ["http://localhost:*", "http://127.0.0.1:*"]
REQUIRED_ENV = (
    "MCP_BASE_URL",
    "GITHUB_CLIENT_ID",
    "GITHUB_CLIENT_SECRET",
    "MCP_ALLOWED_GITHUB_USERS",
    "MCP_JWT_SIGNING_KEY",
)
MIN_SIGNING_KEY_LENGTH = 32


class AllowlistGitHubProvider(GitHubProvider):
    """GitHubProvider que solo acepta los logins de GitHub de la lista blanca."""

    def __init__(self, *, allowed_logins: set[str], **kwargs):
        super().__init__(**kwargs)
        self.allowed_logins = {login.strip().lower() for login in allowed_logins if login.strip()}

    def is_allowed(self, access_token: AccessToken | None) -> bool:
        if access_token is None:
            return False
        login = (access_token.claims or {}).get("login")
        return isinstance(login, str) and login.lower() in self.allowed_logins

    async def load_access_token(self, token: str) -> AccessToken | None:  # type: ignore[override]
        access_token = await super().load_access_token(token)
        if access_token is None:
            return None
        if not self.is_allowed(access_token):
            login = (access_token.claims or {}).get("login")
            logger.warning("MCP: acceso denegado al usuario de GitHub %r (no está en MCP_ALLOWED_GITHUB_USERS)", login)
            return None
        return access_token


def is_development(env: Mapping[str, str]) -> bool:
    return env.get("MCP_ENV", "").strip().lower() == "development"


def allowed_redirect_uris(env: Mapping[str, str]) -> list[str]:
    """En producción solo el callback de claude.ai; en desarrollo también localhost (Inspector)."""
    uris = [CLAUDE_AI_CALLBACK]
    if is_development(env):
        uris += DEV_REDIRECT_URIS
    return uris


def _mongo_client_storage(env: Mapping[str, str]) -> AsyncKeyValue:
    """Estado OAuth (clientes registrados, transacciones y tokens) en Mongo.

    Así sobrevive a los reinicios de Render y se comparte entre workers de gunicorn.
    """
    from key_value.aio.stores.mongodb import MongoDBStore
    from key_value.aio.stores.mongodb.store import MongoDBV1CollectionSanitizationStrategy

    from app.db.db import DB_NAME

    store = MongoDBStore(
        url=env["MONGOCLUSTER"],
        db_name=DB_NAME,
        collection_sanitization_strategy=MongoDBV1CollectionSanitizationStrategy(),
    )
    return PrefixCollectionsWrapper(key_value=store, prefix="mcp_oauth")


def _encrypted(storage: AsyncKeyValue, signing_key: str) -> AsyncKeyValue:
    """Cifra todo el estado OAuth con una clave derivada (HKDF) de MCP_JWT_SIGNING_KEY.

    Si se rota MCP_JWT_SIGNING_KEY, lo guardado no se puede descifrar y se trata como
    inexistente (no como error): los clientes registrados y los tokens dejan de valer
    y hay que reconectar el conector.
    """
    encryption_key = derive_jwt_key(high_entropy_material=signing_key, salt="portfolio-mcp-oauth-storage")
    return FernetEncryptionWrapper(
        key_value=storage,
        fernet=Fernet(key=encryption_key),
        raise_on_decryption_error=False,
    )


def build_auth_from_env(
    env: Mapping[str, str] | None = None,
    *,
    client_storage: AsyncKeyValue | None = None,
) -> AllowlistGitHubProvider | None:
    env = os.environ if env is None else env

    missing = [name for name in REQUIRED_ENV if not env.get(name, "").strip()]
    if missing:
        logger.warning("MCP desactivado: faltan variables de entorno %s", ", ".join(missing))
        return None

    signing_key = env["MCP_JWT_SIGNING_KEY"]
    if len(signing_key) < MIN_SIGNING_KEY_LENGTH:
        logger.error("MCP desactivado: MCP_JWT_SIGNING_KEY debe tener al menos %d caracteres", MIN_SIGNING_KEY_LENGTH)
        return None

    allowed = {u for u in env["MCP_ALLOWED_GITHUB_USERS"].split(",") if u.strip()}
    if not allowed:
        logger.warning("MCP desactivado: MCP_ALLOWED_GITHUB_USERS está vacío")
        return None

    if client_storage is None:
        if not env.get("MONGOCLUSTER"):
            logger.warning("MCP desactivado: falta MONGOCLUSTER para guardar el estado OAuth")
            return None
        client_storage = _mongo_client_storage(env)

    return AllowlistGitHubProvider(
        allowed_logins=allowed,
        client_id=env["GITHUB_CLIENT_ID"],
        client_secret=env["GITHUB_CLIENT_SECRET"],
        base_url=env["MCP_BASE_URL"].rstrip("/"),
        required_scopes=["read:user"],  # mínimo privilegio: solo leer el perfil
        allowed_client_redirect_uris=allowed_redirect_uris(env),
        client_storage=_encrypted(client_storage, signing_key),
        jwt_signing_key=signing_key,
        require_authorization_consent=True,
    )
