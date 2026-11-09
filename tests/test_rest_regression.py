"""Regresión del REST y del panel: fija el comportamiento externo actual.

Se escribió y se pasó contra el código ANTES de extraer la capa de servicios;
debe seguir pasando sin cambios después del refactor.
"""
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.db.db import collections
from app.main import app
from app.middlewares.session import require_login


@pytest.fixture
def client():
    with TestClient(app, follow_redirects=False) as c:
        yield c


@pytest.fixture
def logged_client(client):
    app.dependency_overrides[require_login] = lambda: "tester"
    yield client
    app.dependency_overrides.pop(require_login, None)


PROJECT_FORM = {
    "nombre": "Portfolio",
    "descripcion": "Mi web",
    "tecnologias": "React, FastAPI ,Mongo",
    "link": "https://vinnievasta.com",
    "github": "https://github.com/x/front",
    "githubBackend": "https://github.com/x/back",
}


# ---------- API pública (la consume el frontend) ----------

@pytest.mark.parametrize(
    "path,attr",
    [
        ("/api/v1/projects", "projects"),
        ("/api/v1/experience", "experience"),
        ("/api/v1/education", "education"),
        ("/api/v1/about_me", "aboutMe"),
    ],
)
def test_api_lists_serialize_id_as_string(client, path, attr):
    col = getattr(collections, attr)
    oid = ObjectId()
    import asyncio
    asyncio.run(col.insert_one({"_id": oid, "nombre": "a", "tecnologias": ["x"]}))

    resp = client.get(path)

    assert resp.status_code == 200
    assert resp.json() == [{"_id": str(oid), "nombre": "a", "tecnologias": ["x"]}]


def test_api_lists_empty(client):
    for path in ("/api/v1/projects", "/api/v1/experience", "/api/v1/education", "/api/v1/about_me"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.json() == []


def test_public_pages(client):
    assert client.get("/").status_code == 200
    assert client.get("/api/v1").status_code == 200
    assert client.get("/login").status_code == 200


def test_protected_routes_redirect_to_login(client):
    for path in ("/show/allProjects", "/edit/experiences", "/show/education", "/aboutMe/edit", "/dashboard"):
        resp = client.get(path)
        assert resp.status_code == 302, path
        assert resp.headers["location"] == "/login"


# ---------- Proyectos ----------

def _only_doc(client, path):
    data = client.get(path).json()
    assert len(data) == 1
    return data[0]


def test_project_add_update_delete(logged_client):
    resp = logged_client.post("/add/new_project", data=PROJECT_FORM)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/show/allProjects?success=added"
    doc = _only_doc(logged_client, "/api/v1/projects")
    assert {k: v for k, v in doc.items() if k != "_id"} == {
        "nombre": "Portfolio",
        "descripcion": "Mi web",
        "tecnologias": ["React", "FastAPI", "Mongo"],
        "link": "https://vinnievasta.com",
        "github": "https://github.com/x/front",
        "githubBackend": "https://github.com/x/back",
        "backendOffline": None,
    }

    resp = logged_client.post(
        f"/update/project/{doc['_id']}",
        data={**PROJECT_FORM, "nombre": "Nuevo", "backendOffline": "true"},
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/show/allProjects?success=updated"
    updated = _only_doc(logged_client, "/api/v1/projects")
    assert updated["_id"] == doc["_id"]
    assert updated["nombre"] == "Nuevo"
    assert updated["backendOffline"] == "true"

    assert logged_client.get("/show/allProjects").status_code == 200
    assert logged_client.get(f"/show/editProject/{doc['_id']}").status_code == 200
    assert logged_client.get("/show/newProject").status_code == 200

    resp = logged_client.post(f"/delete/project/{doc['_id']}")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/show/allProjects?success=deleted"
    assert logged_client.get("/api/v1/projects").json() == []


# ---------- Experiencia ----------

def test_experience_add_update_delete(logged_client):
    form = {
        "empresa": "ACME",
        "periodo": "2023-2024",
        "puesto": "Backend",
        "descripcion": "APIs",
        "tecnologias": "Python, FastAPI",
    }
    resp = logged_client.post("/add/experienceToDDBB", data=form)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/edit/experiences?success=added"
    doc = _only_doc(logged_client, "/api/v1/experience")
    assert {k: v for k, v in doc.items() if k != "_id"} == {
        "empresa": "ACME",
        "periodo": "2023-2024",
        "puesto": "Backend",
        "descripcion": "APIs",
        "tecnologias": ["Python", "FastAPI"],
    }

    resp = logged_client.post("/update/experience", data={**form, "id": doc["_id"], "puesto": "Lead"})
    assert resp.status_code == 303
    assert resp.headers["location"] == "/edit/experiences?success=updated"
    assert _only_doc(logged_client, "/api/v1/experience")["puesto"] == "Lead"

    assert logged_client.get("/edit/experiences").status_code == 200
    assert logged_client.get(f"/edit/experience/{doc['_id']}").status_code == 200
    assert logged_client.get("/add/new_experience").status_code == 200

    resp = logged_client.post(f"/delete/experience/{doc['_id']}")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/edit/experiences?success=deleted"
    assert logged_client.get("/api/v1/experience").json() == []


# ---------- Educación ----------

def test_education_add_update_delete(logged_client):
    form = {
        "titulo": "DAW",
        "institucion": "IES",
        "descripcion": "Desarrollo web",
        "inicio": "2020",
        "fin": "2022",
    }
    resp = logged_client.post("/add/new_education", data=form)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/show/education?success=added"
    doc = _only_doc(logged_client, "/api/v1/education")
    assert {k: v for k, v in doc.items() if k != "_id"} == form  # sin 'estado'

    resp = logged_client.post(
        f"/update/education/{doc['_id']}", data={**form, "fin": "2023", "estado": "Finalizado"}
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/show/education?success=updated"
    updated = _only_doc(logged_client, "/api/v1/education")
    assert updated["fin"] == "2023"
    assert updated["estado"] == "Finalizado"

    assert logged_client.get("/show/education").status_code == 200
    assert logged_client.get(f"/show/updateEducation/{doc['_id']}").status_code == 200
    assert logged_client.get("/show/add_new_education").status_code == 200

    resp = logged_client.post(f"/delete/education/{doc['_id']}")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/show/education?success=deleted"
    assert logged_client.get("/api/v1/education").json() == []


# ---------- Sobre mí ----------

def test_about_me_upsert(logged_client):
    form = {
        "nombre": "Pablo",
        "titulo": "Dev",
        "descripcion": "Hola",
        "softSkills": "Equipo, Comunicación",
        "hardSkills": "Python,FastAPI",
        "idiomas": "Español, Inglés",
    }
    for nombre in ("Pablo", "Pablo V"):
        resp = logged_client.post("/update/aboutMe", data={**form, "nombre": nombre})
        assert resp.status_code == 303
        assert resp.headers["location"] == "/dashboard"

    doc = _only_doc(logged_client, "/api/v1/about_me")  # upsert: sigue habiendo uno
    assert {k: v for k, v in doc.items() if k != "_id"} == {
        "nombre": "Pablo V",
        "titulo": "Dev",
        "descripcion": "Hola",
        "softSkills": ["Equipo", "Comunicación"],
        "hardSkills": ["Python", "FastAPI"],
        "idiomas": ["Español", "Inglés"],
    }
    assert logged_client.get("/aboutMe/edit").status_code == 200
    assert logged_client.get("/dashboard").status_code == 200
