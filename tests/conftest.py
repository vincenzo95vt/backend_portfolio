"""Fixtures compartidas.

Las variables de entorno se fijan ANTES de importar la app: load_dotenv() no
sobrescribe variables ya definidas, así los tests nunca tocan la BD real.
"""
import os

os.environ["MONGOCLUSTER"] = "mongodb://localhost:27017"
os.environ["CLAVESECRETA"] = "test-session-secret"
# Sin configuración OAuth por defecto: app.main se importa con /mcp sin montar
# aunque el .env local tenga estas variables (load_dotenv no pisa las existentes).
for _name in ("MCP_BASE_URL", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET",
              "MCP_ALLOWED_GITHUB_USERS", "MCP_JWT_SIGNING_KEY", "MCP_ENV", "MONGO_DB_NAME"):
    os.environ[_name] = ""

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.db.db import collections


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    """Sustituye cada colección por una colección en memoria (mongomock)."""
    mock = AsyncMongoMockClient()["test_portfolio"]
    monkeypatch.setattr(collections, "projects", mock["Projects"])
    monkeypatch.setattr(collections, "experience", mock["Experience"])
    monkeypatch.setattr(collections, "education", mock["Education"])
    monkeypatch.setattr(collections, "aboutMe", mock["About_me"])
    monkeypatch.setattr(collections, "users", mock["Users"])
    return mock
