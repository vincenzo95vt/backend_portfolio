"""Herramientas MCP probadas con un cliente FastMCP en memoria (sin HTTP ni auth)."""
import pytest
from fastmcp import Client

from app.db.db import collections
from app.mcp.server import create_server

MISSING_ID = "0" * 24

PROJECT = {
    "nombre": "Portfolio",
    "descripcion": "Mi web personal",
    "tecnologias": [" React ", "FastAPI", ""],
    "link": "https://vinnievasta.com",
    "github": "https://github.com/x/front",
}
EXPERIENCE = {
    "empresa": "ACME",
    "periodo": "2023 - Actualidad",
    "puesto": "Backend",
    "descripcion": "APIs",
    "tecnologias": ["Python"],
}
EDUCATION = {
    "titulo": "DAW",
    "institucion": "IES",
    "descripcion": "Desarrollo web",
    "inicio": "2020",
    "fin": "2022",
}


@pytest.fixture
async def client():
    async with Client(create_server()) as c:
        yield c


async def call(client, name, args=None):
    return (await client.call_tool(name, args or {})).structured_content


async def call_error(client, name, args):
    result = await client.call_tool(name, args, raise_on_error=False)
    assert result.is_error, f"{name} debería fallar con {args}"
    return result.content[0].text


# ------------------------------------------------------------ catálogo

async def test_tool_catalog_has_no_delete(client):
    names = {t.name for t in await client.list_tools()}
    assert names == {
        "list_projects", "get_project", "create_project", "update_project",
        "list_experiences", "get_experience", "create_experience", "update_experience",
        "list_educations", "get_education", "create_education", "update_education",
        "get_about_me", "update_about_me",
    }
    assert not any("delete" in n or "remove" in n for n in names)


async def test_tools_have_descriptions_and_annotations(client):
    for tool in await client.list_tools():
        assert tool.description and len(tool.description) > 20, tool.name
        read_only = tool.name.startswith(("list_", "get_"))
        assert tool.annotations.read_only_hint is read_only, tool.name
        assert tool.annotations.destructive_hint is False, tool.name


# ------------------------------------------------------------ proyectos

async def test_project_crud(client):
    created = await call(client, "create_project", {"project": PROJECT})
    assert created["tecnologias"] == ["React", "FastAPI"]
    assert created["githubBackend"] == ""
    assert created["backendOffline"] is False

    listed = (await call(client, "list_projects"))["result"]
    assert [p["id"] for p in listed] == [created["id"]]
    assert await call(client, "get_project", {"id": created["id"]}) == created

    updated = await call(client, "update_project", {"id": created["id"], "changes": {"nombre": "Nuevo", "backendOffline": True}})
    assert updated["nombre"] == "Nuevo"
    assert updated["backendOffline"] is True
    assert updated["descripcion"] == PROJECT["descripcion"]  # update parcial


async def test_project_backend_offline_uses_panel_format(client):
    """El frontend lee backendOffline como "true" / None (formato del panel)."""
    created = await call(client, "create_project", {"project": {**PROJECT, "backendOffline": True}})
    doc = await collections.projects.find_one({})
    assert doc["backendOffline"] == "true"

    await call(client, "update_project", {"id": created["id"], "changes": {"backendOffline": False}})
    doc = await collections.projects.find_one({})
    assert doc["backendOffline"] is None


async def test_project_reads_legacy_documents(client):
    await collections.projects.insert_one({"nombre": "Viejo", "tecnologias": "Python", "backendOffline": None})
    [project] = (await call(client, "list_projects"))["result"]
    assert project["tecnologias"] == ["Python"]
    assert project["backendOffline"] is False
    assert project["link"] == ""


# ------------------------------------------------------------ experiencia y educación

async def test_experience_crud(client):
    created = await call(client, "create_experience", {"experience": EXPERIENCE})
    assert (await call(client, "list_experiences"))["result"] == [created]
    assert await call(client, "get_experience", {"id": created["id"]}) == created
    updated = await call(client, "update_experience", {"id": created["id"], "changes": {"tecnologias": ["Go", "Rust"]}})
    assert updated["tecnologias"] == ["Go", "Rust"]
    assert updated["empresa"] == "ACME"


async def test_education_crud(client):
    created = await call(client, "create_education", {"education": EDUCATION})
    doc = await collections.education.find_one({})
    assert "estado" not in doc  # como el panel: solo se guarda si viene
    assert (await call(client, "list_educations"))["result"] == [created]
    assert await call(client, "get_education", {"id": created["id"]}) == created
    updated = await call(client, "update_education", {"id": created["id"], "changes": {"estado": "Finalizado"}})
    assert updated["estado"] == "Finalizado"
    assert updated["titulo"] == "DAW"


# ------------------------------------------------------------ sobre mí

async def test_about_me_get_empty_then_upsert(client):
    assert (await call(client, "get_about_me"))["exists"] is False

    about = await call(client, "update_about_me", {"changes": {"nombre": "Pablo", "hardSkills": ["Python", " FastAPI "]}})
    assert about["exists"] is True
    assert about["hardSkills"] == ["Python", "FastAPI"]

    about = await call(client, "update_about_me", {"changes": {"idiomas": ["Inglés (B2)"]}})
    assert about["nombre"] == "Pablo"
    assert about["idiomas"] == ["Inglés (B2)"]
    assert await collections.aboutMe.count_documents({}) == 1


# ------------------------------------------------------------ errores legibles

@pytest.mark.parametrize(
    "tool,args",
    [
        ("get_project", {}),
        ("update_project", {"changes": {"nombre": "x"}}),
        ("get_experience", {}),
        ("update_experience", {"changes": {"puesto": "x"}}),
        ("get_education", {}),
        ("update_education", {"changes": {"fin": "x"}}),
    ],
)
async def test_invalid_and_missing_ids(client, tool, args):
    list_tool = {"project": "list_projects", "experience": "list_experiences", "education": "list_educations"}[tool.split("_", 1)[1]]

    msg = await call_error(client, tool, {**args, "id": "no-es-un-id"})
    assert "no es un id válido" in msg and list_tool in msg

    msg = await call_error(client, tool, {**args, "id": MISSING_ID})
    assert f"con id '{MISSING_ID}'" in msg and list_tool in msg


async def test_validation_errors_are_readable(client):
    msg = await call_error(client, "create_project", {"project": {**PROJECT, "nombre": "   "}})
    assert "project.nombre" in msg and "no puede estar vacío" in msg

    msg = await call_error(client, "create_project", {"project": {**PROJECT, "link": "vinnievasta"}})
    assert "project.link" in msg and "no es una URL http(s) válida" in msg

    msg = await call_error(client, "create_project", {"project": {**PROJECT, "precio": 3}})
    assert "project.precio" in msg and "Extra inputs are not permitted" in msg

    msg = await call_error(client, "create_experience", {"experience": {"empresa": "ACME"}})
    assert "experience.puesto" in msg and "Field required" in msg

    msg = await call_error(client, "create_experience", {"experience": {**EXPERIENCE, "tecnologias": [" ", ""]}})
    assert "al menos un elemento" in msg

    created = await call(client, "create_project", {"project": PROJECT})
    for changes in ({}, {"nombre": None}):
        msg = await call_error(client, "update_project", {"id": created["id"], "changes": changes})
        assert "indica al menos un campo" in msg

    msg = await call_error(client, "update_about_me", {"changes": {}})
    assert "indica al menos un campo" in msg

    # Nada de lo anterior ha escrito en la BD
    assert await collections.projects.count_documents({}) == 1
    assert await collections.experience.count_documents({}) == 0
    assert await collections.aboutMe.count_documents({}) == 0


async def test_unexpected_errors_are_masked(client, monkeypatch):
    from app.services import projects_service

    async def boom():
        raise RuntimeError("mongodb://usuario:secreto@cluster")

    monkeypatch.setattr(projects_service, "list", boom)
    msg = await call_error(client, "list_projects", {})
    assert "secreto" not in msg
