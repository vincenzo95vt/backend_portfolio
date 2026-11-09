"""Campo 'orden': ordenación en servicios, REST, panel y herramientas MCP."""
import asyncio

import pytest
from fastapi.testclient import TestClient
from fastmcp import Client

from app.db.db import collections
from app.main import app
from app.mcp.server import create_server
from app.middlewares.session import require_login
from app.services import InvalidOrdenError, parse_orden, sort_by_orden


def names(docs, field="n"):
    return [d[field] for d in docs]


# ------------------------------------------------------------ servicios

def test_sort_by_orden_puts_missing_last_and_is_stable():
    docs = [
        {"n": "a"},                      # sin orden
        {"n": "b", "orden": 2},
        {"n": "c", "orden": None},       # null = sin orden
        {"n": "d", "orden": 1},
        {"n": "e", "orden": "3"},        # no numérico = sin orden
        {"n": "f", "orden": 1},          # empate con d: se mantiene el orden de inserción
        {"n": "g", "orden": True},       # bool no cuenta como número
        {"n": "h", "orden": 0},
        {"n": "i", "orden": 1.5},
    ]
    assert names(sort_by_orden(docs)) == ["h", "d", "f", "i", "b", "a", "c", "e", "g"]


def test_sort_without_any_orden_keeps_insertion_order():
    docs = [{"n": x} for x in "zyxw"]
    assert names(sort_by_orden(docs)) == ["z", "y", "x", "w"]


@pytest.mark.parametrize("raw,expected", [(None, None), ("", None), ("   ", None), ("0", 0), (" 7 ", 7), ("100000", 100000)])
def test_parse_orden_valid(raw, expected):
    assert parse_orden(raw) == expected


@pytest.mark.parametrize("raw", ["abc", "1.5", "-1", "100001"])
def test_parse_orden_invalid(raw):
    with pytest.raises(InvalidOrdenError):
        parse_orden(raw)


# ------------------------------------------------------------ API pública

@pytest.fixture
def client():
    with TestClient(app, follow_redirects=False) as c:
        yield c


@pytest.fixture
def logged_client(client):
    app.dependency_overrides[require_login] = lambda: "tester"
    yield client
    app.dependency_overrides.pop(require_login, None)


def insert(attr, docs):
    asyncio.run(getattr(collections, attr).insert_many([dict(d) for d in docs]))


@pytest.mark.parametrize(
    "path,attr",
    [("/api/v1/projects", "projects"), ("/api/v1/experience", "experience"), ("/api/v1/education", "education")],
)
def test_api_returns_sorted(client, path, attr):
    insert(attr, [{"n": "sin-1"}, {"n": "tercero", "orden": 30}, {"n": "sin-2"}, {"n": "primero", "orden": 10}, {"n": "segundo", "orden": 20}])
    data = client.get(path).json()
    assert names(data) == ["primero", "segundo", "tercero", "sin-1", "sin-2"]
    assert "orden" not in data[3]  # los que no tienen orden no ganan el campo


@pytest.mark.parametrize("path,attr", [("/api/v1/projects", "projects"), ("/api/v1/experience", "experience"), ("/api/v1/education", "education")])
def test_api_without_orden_is_unchanged(client, path, attr):
    insert(attr, [{"n": "a"}, {"n": "b"}, {"n": "c"}])
    assert names(client.get(path).json()) == ["a", "b", "c"]


# ------------------------------------------------------------ panel

PANEL = {
    "projects": {
        "create": "/add/new_project",
        "update": lambda doc_id: (f"/update/project/{doc_id}", {}),
        "edit_page": lambda doc_id: f"/show/editProject/{doc_id}",
        "api": "/api/v1/projects",
        # El panel exige las tres URLs: FastAPI trata un campo de formulario vacío como ausente
        # (comportamiento previo, también con FastAPI 0.115).
        "form": {"nombre": "P", "descripcion": "d", "tecnologias": "a", "link": "https://a.example",
                 "github": "https://github.com/x/a", "githubBackend": "https://github.com/x/b"},
    },
    "experience": {
        "create": "/add/experienceToDDBB",
        "update": lambda doc_id: ("/update/experience", {"id": doc_id}),
        "edit_page": lambda doc_id: f"/edit/experience/{doc_id}",
        "api": "/api/v1/experience",
        "form": {"empresa": "E", "periodo": "p", "puesto": "x", "descripcion": "d", "tecnologias": "a"},
    },
    "education": {
        "create": "/add/new_education",
        "update": lambda doc_id: (f"/update/education/{doc_id}", {}),
        "edit_page": lambda doc_id: f"/show/updateEducation/{doc_id}",
        "api": "/api/v1/education",
        "form": {"titulo": "T", "institucion": "I", "descripcion": "d", "inicio": "1", "fin": "2"},
    },
}


@pytest.mark.parametrize("entity", PANEL)
def test_panel_create_and_update_orden(logged_client, entity):
    cfg = PANEL[entity]

    # Crear sin orden (campo vacío): el documento no lleva 'orden'
    assert logged_client.post(cfg["create"], data={**cfg["form"], "orden": ""}).status_code == 303
    # Crear con orden
    assert logged_client.post(cfg["create"], data={**cfg["form"], "orden": "5"}).status_code == 303

    first, second = logged_client.get(cfg["api"]).json()
    assert second.get("orden") is None and "orden" not in second  # el sin orden va al final
    assert first["orden"] == 5

    # El formulario de edición muestra el valor
    assert 'name="orden"' in logged_client.get(cfg["edit_page"](first["_id"])).text
    assert 'value="5"' in logged_client.get(cfg["edit_page"](first["_id"])).text

    # Dar orden al que no tenía lo pone delante
    url, extra = cfg["update"](second["_id"])
    assert logged_client.post(url, data={**cfg["form"], **extra, "orden": "1"}).status_code == 303
    data = logged_client.get(cfg["api"]).json()
    assert [d["_id"] for d in data] == [second["_id"], first["_id"]]

    # Vaciar el orden lo elimina y vuelve al final
    url, extra = cfg["update"](second["_id"])
    assert logged_client.post(url, data={**cfg["form"], **extra, "orden": ""}).status_code == 303
    data = logged_client.get(cfg["api"]).json()
    assert [d["_id"] for d in data] == [first["_id"], second["_id"]]
    assert "orden" not in data[1]


@pytest.mark.parametrize("entity", PANEL)
def test_panel_rejects_invalid_orden(logged_client, entity):
    cfg = PANEL[entity]
    resp = logged_client.post(cfg["create"], data={**cfg["form"], "orden": "abc"})
    assert resp.status_code == 400
    assert "orden" in resp.json()["detail"]
    assert logged_client.get(cfg["api"]).json() == []


def test_panel_form_without_orden_field_still_works(logged_client):
    """Un formulario antiguo (sin el campo) sigue funcionando: 'orden' es opcional."""
    assert logged_client.post("/add/new_project", data=PANEL["projects"]["form"]).status_code == 303
    assert "orden" not in logged_client.get("/api/v1/projects").json()[0]


# ------------------------------------------------------------ MCP

MCP_ENTITIES = [
    ("project", "projects", {"nombre": "P", "descripcion": "d", "tecnologias": ["a"]}, "nombre"),
    ("experience", "experiences", {"empresa": "E", "periodo": "p", "puesto": "x", "descripcion": "d", "tecnologias": ["a"]}, "empresa"),
    ("education", "educations", {"titulo": "T", "institucion": "I", "descripcion": "d", "inicio": "1", "fin": "2"}, "titulo"),
]


@pytest.fixture
async def mcp():
    async with Client(create_server()) as c:
        yield c


async def call(mcp, name, args=None):
    return (await mcp.call_tool(name, args or {})).structured_content


@pytest.mark.parametrize("singular,plural,base,label", MCP_ENTITIES)
async def test_mcp_create_list_and_reorder(mcp, singular, plural, base, label):
    created = {}
    for name, orden in [("sin", None), ("dos", 20), ("uno", 10)]:
        payload = {**base, label: name}
        if orden is not None:
            payload["orden"] = orden
        created[name] = await call(mcp, f"create_{singular}", {singular: payload})

    assert created["sin"]["orden"] is None
    assert created["uno"]["orden"] == 10

    listed = (await call(mcp, f"list_{plural}"))["result"]
    assert names(listed, label) == ["uno", "dos", "sin"]

    # Reordenar cambiando solo 'orden'
    updated = await call(mcp, f"update_{singular}", {"id": created["sin"]["id"], "changes": {"orden": 5}})
    assert updated["orden"] == 5 and updated[label] == "sin"
    listed = (await call(mcp, f"list_{plural}"))["result"]
    assert names(listed, label) == ["sin", "uno", "dos"]


async def test_mcp_create_without_orden_does_not_store_field(mcp):
    await call(mcp, "create_project", {"project": MCP_ENTITIES[0][2]})
    await call(mcp, "create_experience", {"experience": MCP_ENTITIES[1][2]})
    await call(mcp, "create_education", {"education": MCP_ENTITIES[2][2]})
    for attr in ("projects", "experience", "education"):
        assert "orden" not in await getattr(collections, attr).find_one({})


@pytest.mark.parametrize("bad", [-1, 100001, "primero"])
async def test_mcp_rejects_invalid_orden(mcp, bad):
    result = await mcp.call_tool("create_project", {"project": {**MCP_ENTITIES[0][2], "orden": bad}}, raise_on_error=False)
    assert result.is_error
    assert "project.orden" in result.content[0].text
    assert await collections.projects.count_documents({}) == 0


async def test_mcp_orden_is_documented_in_schema(mcp):
    tools = {t.name: t for t in await mcp.list_tools()}
    for tool in ("create_project", "update_experience", "create_education"):
        schema = str(tools[tool].input_schema)
        assert "el número más bajo aparece primero" in schema
        assert "al final" in schema


async def test_mcp_legacy_orden_values(mcp):
    await collections.projects.insert_many([
        {"nombre": "texto", "orden": "3"},
        {"nombre": "float", "orden": 2.0},
        {"nombre": "decimal", "orden": 1.5},
    ])
    listed = (await call(mcp, "list_projects"))["result"]
    assert [(p["nombre"], p["orden"]) for p in listed] == [("decimal", None), ("float", 2), ("texto", None)]
