"""
Modulo de conexion a la base de datos Supabase.

Crea un pool de conexiones psycopg2 al inicio del modulo.
Se usa psycopg2 en modo sincrono porque el ADK no soporta
drivers asyncio en su version actual, y porque las queries
de este proyecto no requieren concurrencia en la capa de BD.

No leer DATABASE_URL desde os.environ directamente:
siempre importar desde config.
"""
import logging
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2 import pool as pg_pool

from config import DATABASE_URL

logger = logging.getLogger(__name__)

# Pool con minimo 1 conexion y maximo 5.
# Para una demo de sesion unica, 5 es mas que suficiente.
_pool: pg_pool.SimpleConnectionPool | None = None


def inicializar_pool() -> None:
    """
    Inicializa el pool de conexiones.

    Debe llamarse una vez al arrancar el servidor (en main.py).
    Lanza psycopg2.OperationalError si la BD no es accesible.
    """
    global _pool
    try:
        _pool = pg_pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=DATABASE_URL,
        )
        logger.info("Pool de conexiones a Supabase inicializado correctamente.")
    except psycopg2.OperationalError as e:
        logger.error("No se pudo conectar a Supabase: %s", e)
        raise


def cerrar_pool() -> None:
    """Cierra todas las conexiones del pool. Llamar al apagar el servidor."""
    global _pool
    if _pool:
        _pool.closeall()
        logger.info("Pool de conexiones cerrado.")


@contextmanager
def obtener_conexion() -> Generator:
    """
    Context manager que entrega una conexion del pool y la devuelve al terminar.

    Uso:
        with obtener_conexion() as conn:
            cur = conn.cursor()
            cur.execute("SELECT ...")

    Lanza RuntimeError si el pool no fue inicializado.
    Lanza psycopg2.Error si hay error en la conexion.
    """
    if _pool is None:
        raise RuntimeError(
            "El pool de conexiones no fue inicializado. "
            "Llamar a inicializar_pool() al arrancar el servidor."
        )
    conn = _pool.getconn()
    try:
        yield conn
    except psycopg2.Error as e:
        conn.rollback()
        logger.error("Error en operacion de BD: %s", e)
        raise
    finally:
        _pool.putconn(conn)
