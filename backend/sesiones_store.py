"""
Almacen en memoria de sesiones activas.

Se usa un dict con asyncio.Lock para acceso seguro desde los
endpoints asincronicos de FastAPI. No se usa Redis porque la demo
tiene una sola sesion concurrente y la simplicidad es prioritaria.

Si en el futuro se necesita escalar, este modulo es el unico que
hay que reemplazar por una implementacion con Redis.
"""
import asyncio
import time
import logging
from typing import Optional

from models.schemas import SessionState

logger = logging.getLogger(__name__)

# Dict global: session_id -> dict con el estado
_sesiones: dict[str, dict] = {}
_lock = asyncio.Lock()


async def crear_sesion(estado: SessionState) -> None:
    """Persiste una sesion nueva en el almacen."""
    async with _lock:
        _sesiones[estado.session_id] = estado.model_dump()


async def obtener_sesion(session_id: str) -> Optional[dict]:
    """
    Retorna la sesion si existe y no ha expirado.

    Returns:
        Dict con el estado de la sesion, o None si no existe o expiro.
    """
    async with _lock:
        sesion = _sesiones.get(session_id)
        return dict(sesion) if sesion else None


async def actualizar_sesion(session_id: str, cambios: dict) -> None:
    """Aplica cambios parciales a una sesion existente."""
    async with _lock:
        if session_id in _sesiones:
            _sesiones[session_id].update(cambios)


def obtener_sesion_sync(session_id: str) -> Optional[dict]:
    """
    Version sincronica para uso dentro de tools ADK (no async).

    Las tools de ADK son funciones sincronicas, por lo que no pueden
    usar 'await'. Esta funcion accede al dict directamente sin lock,
    lo cual es aceptable porque en la demo solo hay una sesion activa.
    """
    return _sesiones.get(session_id)


def limpiar_sesiones_expiradas(ttl_minutos: int) -> None:
    """
    Elimina sesiones que superan el TTL.

    Llamada por el BackgroundTask cada 10 minutos.
    """
    ahora = time.time()
    ttl_segundos = ttl_minutos * 60
    expiradas = [
        sid for sid, s in _sesiones.items()
        if ahora - s.get("created_at", ahora) > ttl_segundos
    ]
    for sid in expiradas:
        del _sesiones[sid]
        logger.info("Sesion expirada eliminada: %s", sid)


# Exponer el dict para que los runners de agentes puedan modificarlo
# directamente desde sus tools sincronicas.
# Las tools guardan el resultado en _sesiones[session_id] directamente.
SESIONES = _sesiones
