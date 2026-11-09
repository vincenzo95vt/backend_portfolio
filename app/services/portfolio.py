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
        return [serialize(doc) async for doc in self.collection.find({})]

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
        self, raw_id: str, data: dict[str, Any], *, missing_ok: bool = False
    ) -> dict[str, Any] | None:
        """``$set`` parcial. Lanza NotFoundError si no existe (salvo ``missing_ok``)."""
        oid = parse_object_id(raw_id)
        result = await self.collection.update_one({"_id": oid}, {"$set": data})
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
