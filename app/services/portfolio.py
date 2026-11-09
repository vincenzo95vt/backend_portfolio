"""Acceso a datos del portfolio, compartido por el panel/REST y el servidor MCP.

Las colecciones se resuelven en cada llamada (``getattr(collections, ...)``) en
lugar de al importar, para que los tests puedan sustituirlas.
"""
from __future__ import annotations

from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from app.db.db import collections


class InvalidIdError(ValueError):
    """El identificador no es un ObjectId válido."""

    def __init__(self, raw_id: str):
        self.raw_id = raw_id
        super().__init__(f"'{raw_id}' no es un id válido (ObjectId de 24 caracteres hexadecimales)")


class NotFoundError(LookupError):
    """No existe ningún documento con ese id."""

    def __init__(self, raw_id: str):
        self.raw_id = raw_id
        super().__init__(f"No existe ningún documento con id '{raw_id}'")


def parse_object_id(raw_id: str) -> ObjectId:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError) as exc:
        raise InvalidIdError(str(raw_id)) from exc


class InvalidOrdenError(ValueError):
    """El valor de 'orden' no es un entero >= 0."""


ORDEN_MAX = 100_000


def parse_orden(raw: str | None) -> int | None:
    """Valor del campo 'orden' de un formulario: vacío -> None, si no un entero 0..ORDEN_MAX."""
    if raw is None or not raw.strip():
        return None
    try:
        value = int(raw.strip())
    except ValueError:
        raise InvalidOrdenError(f"'orden' debe ser un número entero, no '{raw}'") from None
    if not 0 <= value <= ORDEN_MAX:
        raise InvalidOrdenError(f"'orden' debe estar entre 0 y {ORDEN_MAX}")
    return value


def orden_value(doc: dict[str, Any]) -> int | float | None:
    """El 'orden' del documento si es numérico; cualquier otra cosa cuenta como "sin orden"."""
    value = doc.get("orden")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def sort_by_orden(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Menor 'orden' primero; los documentos sin 'orden' al final.

    sorted() es estable: en empates (y entre los que no tienen 'orden') se conserva
    el orden en que Mongo los devuelve, es decir, el de inserción, como antes.
    """
    def key(doc):
        value = orden_value(doc)
        return (1, 0) if value is None else (0, value)

    return sorted(docs, key=key)


def split_csv(value: str) -> list[str]:
    """'a, b ,c' -> ['a', 'b', 'c'] (mismo comportamiento que tenían los formularios)."""
    return [item.strip() for item in value.split(",")]


def serialize(doc: dict[str, Any]) -> dict[str, Any]:
    doc["_id"] = str(doc["_id"])
    return doc


class CollectionService:
    """Operaciones sobre una colección de documentos independientes."""

    def __init__(self, collection_attr: str):
        self._collection_attr = collection_attr

    @property
    def collection(self):
        return getattr(collections, self._collection_attr)

    async def list(self) -> list[dict[str, Any]]:
        """Todos los documentos, ordenados por 'orden' (los que no lo tienen, al final)."""
        return sort_by_orden([serialize(doc) async for doc in self.collection.find({})])

    async def find(self, raw_id: str) -> dict[str, Any] | None:
        doc = await self.collection.find_one({"_id": parse_object_id(raw_id)})
        return serialize(doc) if doc else None

    async def get(self, raw_id: str) -> dict[str, Any]:
        doc = await self.find(raw_id)
        if doc is None:
            raise NotFoundError(raw_id)
        return doc

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        doc = dict(data)  # insert_one añade _id al dict: no mutamos el del llamante
        result = await self.collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc

    async def update(
        self,
        raw_id: str,
        data: dict[str, Any],
        *,
        unset: tuple[str, ...] = (),
        missing_ok: bool = False,
    ) -> dict[str, Any] | None:
        """``$set`` parcial (y ``$unset`` de ``unset``). Lanza NotFoundError si no existe (salvo ``missing_ok``)."""
        oid = parse_object_id(raw_id)
        operations: dict[str, Any] = {}
        if data:
            operations["$set"] = data
        if unset:
            operations["$unset"] = {field: "" for field in unset}
        if not operations:
            return await self.get(raw_id)
        result = await self.collection.update_one({"_id": oid}, operations)
        if result.matched_count == 0:
            if missing_ok:
                return None
            raise NotFoundError(raw_id)
        return await self.get(raw_id)

    async def delete(self, raw_id: str) -> bool:
        """Solo lo usa el panel. No se expone por MCP."""
        result = await self.collection.delete_one({"_id": parse_object_id(raw_id)})
        return result.deleted_count > 0


class SingletonService:
    """Colección con un único documento (About me)."""

    def __init__(self, collection_attr: str):
        self._collection_attr = collection_attr

    @property
    def collection(self):
        return getattr(collections, self._collection_attr)

    async def list(self) -> list[dict[str, Any]]:
        return [serialize(doc) async for doc in self.collection.find({})]

    async def get(self) -> dict[str, Any] | None:
        doc = await self.collection.find_one({})
        return serialize(doc) if doc else None

    async def update(self, data: dict[str, Any]) -> dict[str, Any]:
        """``$set`` parcial con upsert, como el formulario del panel."""
        await self.collection.update_one({}, {"$set": data}, upsert=True)
        return await self.get()


projects_service = CollectionService("projects")
experience_service = CollectionService("experience")
education_service = CollectionService("education")
about_service = SingletonService("aboutMe")
