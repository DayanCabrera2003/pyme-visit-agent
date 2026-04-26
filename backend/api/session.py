"""
Router para gestion de sesiones de usuario.

Una sesion representa el flujo completo de un ejecutivo desde el login
hasta el plan final. El estado persiste en memoria durante la sesion.
"""
import logging

from fastapi import APIRouter, HTTPException

from db import queries
from models.schemas import (
    EstadoSesion,
    IniciarSesionRequest,
    IniciarSesionResponse,
    SessionState,
)
from sesiones_store import crear_sesion, obtener_sesion

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/start", response_model=IniciarSesionResponse)
async def iniciar_sesion(request: IniciarSesionRequest):
    """
    Crea una nueva sesion para el ejecutivo indicado.

    Verifica que el ejecutivo existe en la BD y carga su cartera inicial.
    Retorna el session_id que el frontend debe conservar para todo el flujo.
    """
    try:
        # Verificar que el ejecutivo existe en la BD
        ejecutivos = queries.obtener_ejecutivos()
        nombres = [e["nombre_ejecutivo"] for e in ejecutivos]
        if request.nombre_ejecutivo not in nombres:
            raise HTTPException(
                status_code=404,
                detail=f"El ejecutivo '{request.nombre_ejecutivo}' no existe en el sistema.",
            )

        # Cargar cartera para saber el numero de empresas
        cartera = queries.obtener_cartera_ejecutivo(request.nombre_ejecutivo)
        if not cartera:
            raise HTTPException(
                status_code=404,
                detail=f"El ejecutivo '{request.nombre_ejecutivo}' no tiene empresas asignadas.",
            )

        # Obtener sucursal del ejecutivo
        ejecutivo = next(
            e for e in ejecutivos if e["nombre_ejecutivo"] == request.nombre_ejecutivo
        )

        # Crear sesion
        sesion = SessionState(
            nombre_ejecutivo=request.nombre_ejecutivo,
            sucursal=ejecutivo["sucursal"],
        )
        await crear_sesion(sesion)

        logger.info(
            "Sesion creada para '%s': %s (%d empresas)",
            request.nombre_ejecutivo, sesion.session_id, len(cartera)
        )

        return IniciarSesionResponse(
            session_id=sesion.session_id,
            nombre_ejecutivo=sesion.nombre_ejecutivo,
            sucursal=sesion.sucursal,
            n_empresas_cartera=len(cartera),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error al iniciar sesion: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Error al conectar con la base de datos. Intenta nuevamente.",
        )


@router.get("/{session_id}")
async def obtener_estado_sesion(session_id: str):
    """
    Retorna el estado actual de una sesion.

    Usado por el frontend para recuperar el estado si la conexion se pierde.
    Retorna 410 Gone si la sesion expiro o no existe.
    """
    sesion = await obtener_sesion(session_id)
    if sesion is None:
        raise HTTPException(
            status_code=410,
            detail="La sesion expiro o no existe. Vuelve a ingresar.",
        )
    # No retornar datos sensibles de BD en este endpoint
    return {
        "session_id": sesion["session_id"],
        "nombre_ejecutivo": sesion["nombre_ejecutivo"],
        "sucursal": sesion["sucursal"],
        "estado": sesion["estado"],
    }
