"""Fixtures compartidos entre todos los tests del backend."""
import pytest
from db.connection import inicializar_pool, cerrar_pool


@pytest.fixture(scope="session", autouse=True)
def pool_bd():
    """
    Inicializa el pool de BD una vez por sesion de tests.

    Se marca autouse para que todos los tests que necesiten BD
    la tengan disponible sin pedirla explicitamente.
    """
    inicializar_pool()
    yield
    cerrar_pool()
