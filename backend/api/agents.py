"""
Router para los endpoints de streaming SSE y aprobacion de agentes.

Cada agente tiene dos endpoints:
- GET /agent/{n}/stream : SSE que ejecuta el agente y streamea el razonamiento
- POST /agent/{n}/approve : recibe la aprobacion del ejecutivo y avanza el estado
"""
import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agents.agent1_analista import Agente1Runner
from agents.agent2_estratega import Agente2Runner
from agents.agent3_briefs import Agente3Runner
from models.schemas import AprobacionRequest, EstadoSesion
from sesiones_store import SESIONES, actualizar_sesion, obtener_sesion

logger = logging.getLogger(__name__)
router = APIRouter()


def _verificar_sesion_sync(session_id: str) -> dict:
    """
    Verifica que la sesion existe (version sincronica para generadores SSE).

    Retorna el dict de sesion o lanza HTTPException 410.
    """
    sesion = SESIONES.get(session_id)
    if sesion is None:
        raise HTTPException(
            status_code=410,
            detail="La sesion expiro o no existe. Vuelve a ingresar.",
        )
    return sesion


async def _generar_sse(runner_instance, metodo_ejecutar, *args):
    """
    Generador generico de eventos SSE a partir de un runner de agente.

    Lee del queue del runner y convierte cada evento al formato SSE.
    Envia headers de keep-alive para evitar timeouts del navegador.

    Args:
        runner_instance: Instancia de Agente1Runner, 2 o 3.
        metodo_ejecutar: Metodo async del runner que ejecuta el agente.
        *args: Argumentos para el metodo de ejecucion.
    """
    tarea = asyncio.create_task(metodo_ejecutar(*args))

    try:
        while True:
            try:
                # Timeout de 30s para detectar si el agente se colgo
                evento = await asyncio.wait_for(
                    runner_instance.queue.get(), timeout=30.0
                )
            except asyncio.TimeoutError:
                # Enviar comentario SSE para mantener la conexion viva
                yield ": keep-alive\n\n"
                continue

            tipo = evento.get("tipo")

            if tipo == "token":
                # Tokens del LLM no se exponen al frontend (se muestran como progreso estructurado)
                pass

            elif tipo == "progreso":
                data = json.dumps({"paso": evento["paso"], "mensaje": evento["mensaje"]}, ensure_ascii=False)
                yield f"event: progreso\ndata: {data}\n\n"

            elif tipo == "resultado":
                data = json.dumps({"items": evento["items"]}, ensure_ascii=False, default=str)
                yield f"event: resultado\ndata: {data}\n\n"

            elif tipo == "error":
                data = json.dumps({"mensaje": evento["mensaje"]}, ensure_ascii=False)
                yield f"event: error\ndata: {data}\n\n"
                break

            elif tipo == "done":
                yield "event: done\ndata: {}\n\n"
                break

    finally:
        tarea.cancel()


# --- Agente 1 ---

@router.get("/1/stream")
async def stream_agente1(session_id: str):
    """
    SSE: ejecuta el Agente 1 y streamea el razonamiento en tiempo real.

    El cliente debe conectarse con EventSource y escuchar eventos:
    token, resultado, error, done.
    """
    sesion = _verificar_sesion_sync(session_id)
    nombre_ejecutivo = sesion["nombre_ejecutivo"]

    await actualizar_sesion(session_id, {"estado": EstadoSesion.AGENTE1_EJECUTANDO})

    runner = Agente1Runner(sesiones=SESIONES, session_id=session_id)

    return StreamingResponse(
        _generar_sse(runner, runner.ejecutar, nombre_ejecutivo),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Deshabilita buffering en nginx
        },
    )


@router.post("/1/approve")
async def aprobar_agente1(request: AprobacionRequest):
    """
    Registra la aprobacion del ejecutivo sobre el ranking del Agente 1.

    Construye ranking_aprobado como diferencia entre cartera_completa
    y elementos_descartados, preservando el orden del ranking original.
    """
    sesion = SESIONES.get(request.session_id)
    if sesion is None:
        raise HTTPException(status_code=410, detail="Sesion no encontrada o expirada.")

    cartera = sesion.get("cartera_completa", [])
    descartados = set(request.elementos_descartados)

    # Filtrar conservando el orden del ranking
    ranking_aprobado = [
        e for e in cartera if e["rut_empresa"] not in descartados
    ]

    await actualizar_sesion(request.session_id, {
        "ranking_aprobado": ranking_aprobado,
        "comentario_1": request.comentario,
        "estado": EstadoSesion.AGENTE2_EJECUTANDO,
    })

    logger.info(
        "Agente 1 aprobado: %d/%d empresas para sesion %s",
        len(ranking_aprobado), len(cartera), request.session_id
    )
    return {"aprobado": True, "n_empresas": len(ranking_aprobado)}


# --- Agente 2 ---

@router.get("/2/stream")
async def stream_agente2(session_id: str):
    """SSE: ejecuta el Agente 2 con el ranking aprobado del Agente 1."""
    sesion = _verificar_sesion_sync(session_id)
    ranking_aprobado = sesion.get("ranking_aprobado", [])
    comentario = sesion.get("comentario_1", "")

    await actualizar_sesion(session_id, {"estado": EstadoSesion.AGENTE2_EJECUTANDO})

    runner = Agente2Runner(sesiones=SESIONES, session_id=session_id)

    return StreamingResponse(
        _generar_sse(runner, runner.ejecutar, ranking_aprobado, comentario),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/2/approve")
async def aprobar_agente2(request: AprobacionRequest):
    """Registra la aprobacion del ejecutivo sobre la shortlist del Agente 2."""
    sesion = SESIONES.get(request.session_id)
    if sesion is None:
        raise HTTPException(status_code=410, detail="Sesion no encontrada o expirada.")

    visitas = sesion.get("visitas_seleccionadas", [])
    descartados = set(request.elementos_descartados)
    visitas_aprobadas = [v for v in visitas if v["rut_empresa"] not in descartados]

    await actualizar_sesion(request.session_id, {
        "visitas_seleccionadas": visitas_aprobadas,
        "comentario_2": request.comentario,
        "estado": EstadoSesion.AGENTE3_EJECUTANDO,
    })

    return {"aprobado": True, "n_visitas": len(visitas_aprobadas)}


# --- Agente 3 ---

@router.get("/3/stream")
async def stream_agente3(session_id: str):
    """SSE: ejecuta el Agente 3 y genera los briefs finales."""
    sesion = _verificar_sesion_sync(session_id)
    visitas = sesion.get("visitas_seleccionadas", [])
    comentario = sesion.get("comentario_2", "")

    await actualizar_sesion(session_id, {"estado": EstadoSesion.AGENTE3_EJECUTANDO})

    runner = Agente3Runner(sesiones=SESIONES, session_id=session_id)

    return StreamingResponse(
        _generar_sse(runner, runner.ejecutar, visitas, comentario),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
