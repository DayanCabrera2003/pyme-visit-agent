"""
Punto de entrada del backend FastAPI.

Solo inicializacion: configura el app, monta los routers,
inicializa el pool de BD y programa la limpieza de sesiones.
No contiene logica de negocio.
"""
import asyncio
import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import PORT, SESSION_TTL_MINUTES
from db.connection import cerrar_pool, inicializar_pool
from sesiones_store import limpiar_sesiones_expiradas
from api import ejecutivos, session, agents, export

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def tarea_limpieza_sesiones():
    """
    Background task que limpia sesiones expiradas cada 10 minutos.

    Se ejecuta en el event loop de FastAPI para no bloquear requests.
    Usa asyncio.sleep en lugar de threading para mantener todo en el
    mismo loop asincrono.
    """
    while True:
        await asyncio.sleep(600)  # 10 minutos
        limpiar_sesiones_expiradas(SESSION_TTL_MINUTES)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa recursos al arrancar y los libera al apagar."""
    # Arranque
    inicializar_pool()
    logger.info("Pool de BD inicializado.")

    # Lanzar limpieza de sesiones como tarea de fondo
    tarea = asyncio.create_task(tarea_limpieza_sesiones())
    logger.info("Tarea de limpieza de sesiones iniciada.")

    yield

    # Apagado
    tarea.cancel()
    cerrar_pool()
    logger.info("Pool de BD cerrado.")


app = FastAPI(
    title="Planificador de Visitas PYME",
    description="API para el sistema de priorizacion de visitas al segmento PYME bancario.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: permite al frontend en puerto 3000 comunicarse con la API.
# En produccion, restringir origins al dominio real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montaje de routers — cada uno tiene prefix propio
app.include_router(ejecutivos.router, prefix="/ejecutivos", tags=["Ejecutivos"])
app.include_router(session.router, prefix="/session", tags=["Sesion"])
app.include_router(agents.router, prefix="/agent", tags=["Agentes"])
app.include_router(export.router, prefix="/plan", tags=["Exportacion"])


@app.get("/health")
async def health():
    """Endpoint de health check para Docker y monitoreo."""
    return {"status": "ok"}
