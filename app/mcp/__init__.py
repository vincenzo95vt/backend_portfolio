"""Servidor MCP remoto (Streamable HTTP) montado en /mcp."""
from __future__ import annotations

import os
from collections.abc import Mapping

from starlette.applications import Starlette

from app.mcp.auth import build_auth_from_env
from app.mcp.server import create_server

__all__ = ["build_mcp_app", "create_server"]


def build_mcp_app(env: Mapping[str, str] | None = None, **auth_kwargs) -> Starlette | None:
    """App ASGI del servidor MCP protegida con OAuth, o None si no está configurado."""
    auth = build_auth_from_env(os.environ if env is None else env, **auth_kwargs)
    if auth is None:
        return None
    # stateless_http: sin sesiones MCP en memoria; cualquier worker de gunicorn
    # puede atender cualquier petición.
    return create_server(auth=auth).http_app(path="/mcp", stateless_http=True)
