"""Helpers para los formularios del panel."""
from fastapi import HTTPException

from app.services import InvalidOrdenError, parse_orden


def form_orden(raw: str | None) -> int | None:
    """Campo 'orden' del formulario: vacío -> None; inválido -> 400 con mensaje claro."""
    try:
        return parse_orden(raw)
    except InvalidOrdenError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


def apply_orden_on_create(data: dict, orden: int | None) -> dict:
    """Al crear, 'orden' solo se guarda si viene (sin él, el documento queda igual que antes)."""
    if orden is not None:
        data["orden"] = orden
    return data


def orden_update_args(data: dict, orden: int | None) -> dict:
    """Al editar, un 'orden' vacío lo elimina (el elemento pasa al final)."""
    if orden is not None:
        data["orden"] = orden
        return {}
    return {"unset": ("orden",)}
