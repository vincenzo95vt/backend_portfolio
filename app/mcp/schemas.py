"""Esquemas Pydantic de entrada/salida de las herramientas MCP.

Las descripciones de los campos llegan al modelo en el JSON Schema de cada
herramienta: deben explicar qué va en cada campo y en qué formato.
"""
from __future__ import annotations

from typing import Annotated, Any

from app.services import ORDEN_MAX
from pydantic import (
    AfterValidator,
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)

_http_url = TypeAdapter(AnyHttpUrl)


def _strip_nonempty(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("no puede estar vacío ni ser solo espacios")
    return value


def _optional_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    try:
        _http_url.validate_python(value)
    except ValidationError:
        raise ValueError(f"'{value}' no es una URL http(s) válida (ej: https://github.com/usuario/repo)") from None
    return value


def _clean_list(values: list[str]) -> list[str]:
    cleaned = [v.strip() for v in values if v.strip()]
    if not cleaned:
        raise ValueError("debe contener al menos un elemento no vacío")
    return cleaned


Text = Annotated[str, AfterValidator(_strip_nonempty)]
ShortText = Annotated[str, Field(max_length=200), AfterValidator(_strip_nonempty)]
LongText = Annotated[str, Field(max_length=10_000), AfterValidator(_strip_nonempty)]
UrlText = Annotated[str, Field(max_length=500), AfterValidator(_optional_url)]
StrList = Annotated[
    list[Annotated[str, Field(max_length=100)]],
    Field(max_length=100),
    AfterValidator(_clean_list),
]


_ORDEN = (
    "Posición en la web: el número más bajo aparece primero (0 o 1 = el primero). "
    "Los elementos sin orden se muestran al final, en orden de creación. "
    "Para reordenar, lee la lista actual y asigna un número a cada elemento; "
    "conviene usar saltos de 10 (10, 20, 30…) para poder colocar uno nuevo entre medias "
    "sin renumerar el resto."
)
Orden = Annotated[int, Field(ge=0, le=ORDEN_MAX)]


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Update(_Input):
    @model_validator(mode="after")
    def _at_least_one_field(self):
        if not self.changes():
            fields = ", ".join(type(self).model_fields)
            raise ValueError(f"indica al menos un campo a modificar con un valor no nulo ({fields})")
        return self

    def changes(self) -> dict[str, Any]:
        """Solo los campos enviados con valor (update parcial; null = no tocar)."""
        return self.model_dump(include=self.model_fields_set, exclude_none=True)


# ---------------------------------------------------------------- Proyectos

_P_NOMBRE = "Nombre del proyecto"
_P_DESC = "Descripción del proyecto (texto libre)"
_P_TEC = "Tecnologías usadas, una por elemento (ej: ['React', 'FastAPI'])"
_P_LINK = "URL pública del proyecto desplegado, o cadena vacía si no tiene"
_P_GH = "URL del repositorio de GitHub (frontend o principal), o cadena vacía"
_P_GHB = "URL del repositorio de GitHub del backend, o cadena vacía"
_P_OFF = "true si el backend del proyecto está apagado/offline (la web lo indica)"


class ProjectCreate(_Input):
    nombre: ShortText = Field(description=_P_NOMBRE)
    descripcion: LongText = Field(description=_P_DESC)
    tecnologias: StrList = Field(description=_P_TEC)
    link: UrlText = Field("", description=_P_LINK)
    github: UrlText = Field("", description=_P_GH)
    githubBackend: UrlText = Field("", description=_P_GHB)
    backendOffline: bool = Field(False, description=_P_OFF)
    orden: Orden | None = Field(None, description=_ORDEN)


class ProjectUpdate(_Update):
    nombre: ShortText | None = Field(None, description=_P_NOMBRE)
    descripcion: LongText | None = Field(None, description=_P_DESC)
    tecnologias: StrList | None = Field(None, description=_P_TEC + ". Sustituye la lista completa")
    link: UrlText | None = Field(None, description=_P_LINK)
    github: UrlText | None = Field(None, description=_P_GH)
    githubBackend: UrlText | None = Field(None, description=_P_GHB)
    backendOffline: bool | None = Field(None, description=_P_OFF)
    orden: Orden | None = Field(None, description=_ORDEN)


class Project(BaseModel):
    id: str
    nombre: str = ""
    descripcion: str = ""
    tecnologias: list[str] = []
    link: str = ""
    github: str = ""
    githubBackend: str = ""
    backendOffline: bool = False
    orden: int | None = Field(None, description="Posición en la web (menor = antes); null = sin orden, va al final")


# --------------------------------------------------------------- Experiencia

_E_EMP = "Empresa"
_E_PER = "Periodo en texto libre, tal como se mostrará (ej: 'Ene 2023 - Actualidad')"
_E_PUE = "Puesto o rol"
_E_DESC = "Descripción de responsabilidades y logros"
_E_TEC = "Tecnologías usadas, una por elemento"


class ExperienceCreate(_Input):
    empresa: ShortText = Field(description=_E_EMP)
    periodo: ShortText = Field(description=_E_PER)
    puesto: ShortText = Field(description=_E_PUE)
    descripcion: LongText = Field(description=_E_DESC)
    tecnologias: StrList = Field(description=_E_TEC)
    orden: Orden | None = Field(None, description=_ORDEN)


class ExperienceUpdate(_Update):
    empresa: ShortText | None = Field(None, description=_E_EMP)
    periodo: ShortText | None = Field(None, description=_E_PER)
    puesto: ShortText | None = Field(None, description=_E_PUE)
    descripcion: LongText | None = Field(None, description=_E_DESC)
    tecnologias: StrList | None = Field(None, description=_E_TEC + ". Sustituye la lista completa")
    orden: Orden | None = Field(None, description=_ORDEN)


class Experience(BaseModel):
    id: str
    empresa: str = ""
    periodo: str = ""
    puesto: str = ""
    descripcion: str = ""
    tecnologias: list[str] = []
    orden: int | None = Field(None, description="Posición en la web (menor = antes); null = sin orden, va al final")


# ----------------------------------------------------------------- Educación

_ED_TIT = "Título o nombre de la formación"
_ED_INS = "Institución o centro"
_ED_DESC = "Descripción de la formación"
_ED_INI = "Fecha o año de inicio, en texto (ej: '2020' o 'Sep 2020')"
_ED_FIN = "Fecha o año de fin, en texto (ej: '2022' o 'En curso')"
_ED_EST = "Estado opcional (ej: 'Finalizado', 'En curso')"


class EducationCreate(_Input):
    titulo: ShortText = Field(description=_ED_TIT)
    institucion: ShortText = Field(description=_ED_INS)
    descripcion: LongText = Field(description=_ED_DESC)
    inicio: ShortText = Field(description=_ED_INI)
    fin: ShortText = Field(description=_ED_FIN)
    estado: ShortText | None = Field(None, description=_ED_EST)
    orden: Orden | None = Field(None, description=_ORDEN)


class EducationUpdate(_Update):
    titulo: ShortText | None = Field(None, description=_ED_TIT)
    institucion: ShortText | None = Field(None, description=_ED_INS)
    descripcion: LongText | None = Field(None, description=_ED_DESC)
    inicio: ShortText | None = Field(None, description=_ED_INI)
    fin: ShortText | None = Field(None, description=_ED_FIN)
    estado: ShortText | None = Field(None, description=_ED_EST)
    orden: Orden | None = Field(None, description=_ORDEN)


class Education(BaseModel):
    id: str
    titulo: str = ""
    institucion: str = ""
    descripcion: str = ""
    inicio: str = ""
    fin: str = ""
    estado: str | None = None
    orden: int | None = Field(None, description="Posición en la web (menor = antes); null = sin orden, va al final")


# ------------------------------------------------------------------ Sobre mí

_A_NOM = "Nombre completo"
_A_TIT = "Titular profesional (ej: 'Desarrollador Full Stack')"
_A_DESC = "Texto de presentación"
_A_SOFT = "Soft skills, una por elemento. Sustituye la lista completa"
_A_HARD = "Hard skills técnicas, una por elemento. Sustituye la lista completa"
_A_IDI = "Idiomas con nivel, uno por elemento (ej: 'Inglés (B2)'). Sustituye la lista completa"


class AboutMeUpdate(_Update):
    nombre: ShortText | None = Field(None, description=_A_NOM)
    titulo: ShortText | None = Field(None, description=_A_TIT)
    descripcion: LongText | None = Field(None, description=_A_DESC)
    softSkills: StrList | None = Field(None, description=_A_SOFT)
    hardSkills: StrList | None = Field(None, description=_A_HARD)
    idiomas: StrList | None = Field(None, description=_A_IDI)


class AboutMe(BaseModel):
    exists: bool = Field(description="false si todavía no se ha creado la sección 'Sobre mí'")
    nombre: str = ""
    titulo: str = ""
    descripcion: str = ""
    softSkills: list[str] = []
    hardSkills: list[str] = []
    idiomas: list[str] = []
