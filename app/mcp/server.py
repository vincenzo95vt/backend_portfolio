"""Servidor MCP del portfolio: herramientas acotadas list/get/create/update.

No hay herramientas de borrado: a propósito.
"""
from __future__ import annotations

from typing import Annotated, Any, TypeVar

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AuthProvider
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from app.mcp.schemas import (
    AboutMe,
    AboutMeUpdate,
    Education,
    EducationCreate,
    EducationUpdate,
    Experience,
    ExperienceCreate,
    ExperienceUpdate,
    Project,
    ProjectCreate,
    ProjectUpdate,
)
from app.services import (
    CollectionService,
    InvalidIdError,
    NotFoundError,
    about_service,
    education_service,
    experience_service,
    orden_value,
    projects_service,
)

INSTRUCTIONS = """\
Herramientas para leer y editar el contenido del portfolio personal de Pablo
(proyectos, experiencia laboral, formación y la sección 'Sobre mí', que incluye
las skills y los idiomas). Todo lo que cambies se publica en la web.

- Los ids se obtienen con las herramientas list_*; no los inventes.
- Proyectos, experiencias y formación se muestran por el campo `orden`
  (menor número primero; sin orden, al final). Las list_* ya devuelven ese orden.
  Para reordenar, usa update_* cambiando solo `orden`.
- Las herramientas update_* son parciales: envía solo los campos que cambian.
  Los campos de tipo lista se sustituyen enteros, así que para añadir un elemento
  lee primero el valor actual y envía la lista completa.
- No se puede borrar contenido desde aquí.
"""

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
CREATE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
UPDATE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)

IdParam = Annotated[str, Field(description="id del documento, tal como lo devuelve la herramienta list_* correspondiente")]

M = TypeVar("M", bound=BaseModel)

_TRUTHY = {"true", "on", "1", "yes", "si", "sí"}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _to_model(model: type[M], doc: dict[str, Any]) -> M:
    """Documento de Mongo -> modelo de salida, tolerante con datos antiguos."""
    data: dict[str, Any] = {"id": doc["_id"]} if "id" in model.model_fields else {}
    if "exists" in model.model_fields:
        data["exists"] = True
    for name, field in model.model_fields.items():
        if name in ("id", "exists") or name not in doc:
            continue
        value = doc[name]
        if name == "backendOffline":
            value = value is True or str(value).strip().lower() in _TRUTHY
        elif name == "orden":
            number = orden_value(doc)
            value = int(number) if number is not None and float(number).is_integer() else None
        elif field.annotation == list[str]:
            value = _as_list(value)
        elif value is None and field.default is not None:
            continue
        elif value is not None and not isinstance(value, str):
            value = str(value)
        data[name] = value
    return model(**data)


def _without_empty_orden(data: dict[str, Any]) -> dict[str, Any]:
    """Al crear sin 'orden', no se guarda el campo (igual que desde el panel)."""
    if data.get("orden") is None:
        data.pop("orden", None)
    return data


def _project_to_db(data: dict[str, Any]) -> dict[str, Any]:
    # El panel guarda backendOffline como "true" o None; mantenemos ese formato
    # para que el frontend lo siga leyendo igual.
    if "backendOffline" in data:
        data["backendOffline"] = "true" if data["backendOffline"] else None
    return data


async def _get(service: CollectionService, raw_id: str, entity: str, list_tool: str) -> dict[str, Any]:
    try:
        return await service.get(raw_id)
    except InvalidIdError:
        raise ToolError(
            f"'{raw_id}' no es un id válido: debe ser un ObjectId de 24 caracteres hexadecimales. "
            f"Usa {list_tool} para obtener los ids existentes."
        ) from None
    except NotFoundError:
        raise ToolError(f"No existe {entity} con id '{raw_id}'. Usa {list_tool} para ver los ids existentes.") from None


async def _update(
    service: CollectionService, raw_id: str, changes: dict[str, Any], entity: str, list_tool: str
) -> dict[str, Any]:
    await _get(service, raw_id, entity, list_tool)  # valida id y existencia con mensajes claros
    try:
        return await service.update(raw_id, changes)
    except NotFoundError:  # borrado entre medias desde el panel
        raise ToolError(f"No existe {entity} con id '{raw_id}'. Usa {list_tool} para ver los ids existentes.") from None


def create_server(auth: AuthProvider | None = None) -> FastMCP:
    mcp = FastMCP(
        name="portfolio",
        instructions=INSTRUCTIONS,
        auth=auth,
        mask_error_details=True,  # errores inesperados no filtran detalles internos
    )

    # ------------------------------------------------------------ Proyectos

    @mcp.tool(annotations=READ_ONLY)
    async def list_projects() -> list[Project]:
        """Lista todos los proyectos con sus campos e id, en el orden en que aparecen en la web."""
        return [_to_model(Project, d) for d in await projects_service.list()]

    @mcp.tool(annotations=READ_ONLY)
    async def get_project(id: IdParam) -> Project:
        """Devuelve un proyecto concreto por su id."""
        return _to_model(Project, await _get(projects_service, id, "ningún proyecto", "list_projects"))

    @mcp.tool(annotations=CREATE)
    async def create_project(project: ProjectCreate) -> Project:
        """Crea un proyecto nuevo en el portfolio y lo devuelve con su id."""
        doc = await projects_service.create(_project_to_db(_without_empty_orden(project.model_dump())))
        return _to_model(Project, doc)

    @mcp.tool(annotations=UPDATE)
    async def update_project(id: IdParam, changes: ProjectUpdate) -> Project:
        """Modifica un proyecto existente. Solo se cambian los campos enviados en `changes`."""
        doc = await _update(projects_service, id, _project_to_db(changes.changes()), "ningún proyecto", "list_projects")
        return _to_model(Project, doc)

    # ---------------------------------------------------------- Experiencia

    @mcp.tool(annotations=READ_ONLY)
    async def list_experiences() -> list[Experience]:
        """Lista todas las experiencias laborales con sus campos e id, en el orden en que aparecen en la web."""
        return [_to_model(Experience, d) for d in await experience_service.list()]

    @mcp.tool(annotations=READ_ONLY)
    async def get_experience(id: IdParam) -> Experience:
        """Devuelve una experiencia laboral concreta por su id."""
        return _to_model(Experience, await _get(experience_service, id, "ninguna experiencia", "list_experiences"))

    @mcp.tool(annotations=CREATE)
    async def create_experience(experience: ExperienceCreate) -> Experience:
        """Añade una experiencia laboral nueva y la devuelve con su id."""
        return _to_model(Experience, await experience_service.create(_without_empty_orden(experience.model_dump())))

    @mcp.tool(annotations=UPDATE)
    async def update_experience(id: IdParam, changes: ExperienceUpdate) -> Experience:
        """Modifica una experiencia laboral existente. Solo se cambian los campos enviados en `changes`."""
        doc = await _update(experience_service, id, changes.changes(), "ninguna experiencia", "list_experiences")
        return _to_model(Experience, doc)

    # ------------------------------------------------------------ Educación

    @mcp.tool(annotations=READ_ONLY)
    async def list_educations() -> list[Education]:
        """Lista toda la formación (estudios, cursos) con sus campos e id, en el orden en que aparecen en la web."""
        return [_to_model(Education, d) for d in await education_service.list()]

    @mcp.tool(annotations=READ_ONLY)
    async def get_education(id: IdParam) -> Education:
        """Devuelve una formación concreta por su id."""
        return _to_model(Education, await _get(education_service, id, "ninguna formación", "list_educations"))

    @mcp.tool(annotations=CREATE)
    async def create_education(education: EducationCreate) -> Education:
        """Añade una formación nueva y la devuelve con su id."""
        # Igual que el panel: 'estado' solo se guarda si viene.
        data = education.model_dump(exclude_none=True)
        return _to_model(Education, await education_service.create(data))

    @mcp.tool(annotations=UPDATE)
    async def update_education(id: IdParam, changes: EducationUpdate) -> Education:
        """Modifica una formación existente. Solo se cambian los campos enviados en `changes`."""
        doc = await _update(education_service, id, changes.changes(), "ninguna formación", "list_educations")
        return _to_model(Education, doc)

    # ------------------------------------------------------------- Sobre mí

    @mcp.tool(annotations=READ_ONLY)
    async def get_about_me() -> AboutMe:
        """Devuelve la sección 'Sobre mí': nombre, titular, presentación, soft/hard skills e idiomas.

        Es un documento único, por eso no hay list/create: se edita con update_about_me.
        """
        doc = await about_service.get()
        if doc is None:
            return AboutMe(exists=False)
        return _to_model(AboutMe, doc)

    @mcp.tool(annotations=UPDATE)
    async def update_about_me(changes: AboutMeUpdate) -> AboutMe:
        """Modifica la sección 'Sobre mí' (incluye skills e idiomas). Solo cambia los campos enviados.

        Si la sección aún no existe, se crea con los campos enviados.
        """
        return _to_model(AboutMe, await about_service.update(changes.changes()))

    return mcp
