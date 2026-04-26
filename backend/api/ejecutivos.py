"""Router para el listado de ejecutivos PYME."""
import logging

from fastapi import APIRouter, HTTPException

from db import queries
from models.schemas import EjecutivoResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[EjecutivoResponse])
async def listar_ejecutivos():
    """
    Retorna la lista de ejecutivos unicos con su sucursal y regional.

    Usado en el login para el selector de ejecutivo con busqueda.
    """
    try:
        ejecutivos = queries.obtener_ejecutivos()
        return ejecutivos
    except Exception as e:
        logger.error("Error al obtener ejecutivos: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Error al conectar con la base de datos. Intenta nuevamente.",
        )
