"""Fixtures compartidos entre todos los tests del backend."""
import os
import pytest


def pytest_configure(config):
    """
    Establece variables de entorno minimas antes de la coleccion de tests.

    Los tests de agentes y schemas no necesitan credenciales reales.
    Los tests de BD (test_queries) necesitan DATABASE_URL real en .env.
    """
    os.environ.setdefault("GEMINI_API_KEY", "test-dummy-key-for-unit-tests")
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")


@pytest.fixture(scope="session", autouse=True)
def pool_bd():
    """
    Inicializa el pool de BD una vez por sesion de tests.

    Si DATABASE_URL apunta a un servidor inaccesible (tests unitarios),
    la inicializacion falla silenciosamente. Los tests de BD fallaran
    con su propio error; los tests unitarios corren sin problema.
    """
    try:
        from db.connection import inicializar_pool, cerrar_pool
        inicializar_pool()
        yield
        cerrar_pool()
    except Exception:
        yield
