"""
Tests de queries SQL contra la base de datos real de Supabase.

Se usa la BD real porque es de solo lectura y los datos son sinteticos.
Esto verifica que las queries son correctas y la BD es accesible.
Requiere DATABASE_URL definida en el entorno o en .env.
"""
import pytest
from db.connection import inicializar_pool, cerrar_pool
from db import queries


@pytest.fixture(scope="module", autouse=True)
def pool():
    """Inicializa el pool una vez para todos los tests del modulo."""
    inicializar_pool()
    yield
    cerrar_pool()


def test_obtener_ejecutivos_retorna_lista():
    """Debe retornar al menos un ejecutivo de la tabla g4_visitas_pyme."""
    ejecutivos = queries.obtener_ejecutivos()
    assert isinstance(ejecutivos, list)
    assert len(ejecutivos) > 0


def test_ejecutivo_tiene_campos_requeridos():
    """Cada ejecutivo debe tener nombre, sucursal y regional."""
    ejecutivos = queries.obtener_ejecutivos()
    primero = ejecutivos[0]
    assert "nombre_ejecutivo" in primero
    assert "sucursal" in primero
    assert "regional" in primero


def test_obtener_cartera_ejecutivo_retorna_empresas():
    """Debe retornar empresas para un ejecutivo valido."""
    ejecutivos = queries.obtener_ejecutivos()
    nombre = ejecutivos[0]["nombre_ejecutivo"]

    cartera = queries.obtener_cartera_ejecutivo(nombre)
    assert isinstance(cartera, list)
    assert len(cartera) > 0


def test_cartera_empresa_tiene_campos_de_priorizacion():
    """Cada empresa debe tener todos los campos necesarios para calcular el score."""
    ejecutivos = queries.obtener_ejecutivos()
    nombre = ejecutivos[0]["nombre_ejecutivo"]
    cartera = queries.obtener_cartera_ejecutivo(nombre)
    empresa = cartera[0]

    campos_requeridos = [
        "rut_empresa", "razon_social", "score_oportunidad",
        "dias_desde_ultima_visita", "campana_vigente", "mes_peak_negocio",
        "share_of_wallet_pct", "meses_sin_venta", "tipo_oportunidad_principal",
        "tipo_campana_vigente", "excedente_caja_uf",
    ]
    for campo in campos_requeridos:
        assert campo in empresa, f"Campo '{campo}' faltante en empresa"


def test_obtener_detalle_empresa_retorna_todos_los_campos():
    """Debe retornar el detalle completo de una empresa por RUT."""
    ejecutivos = queries.obtener_ejecutivos()
    cartera = queries.obtener_cartera_ejecutivo(ejecutivos[0]["nombre_ejecutivo"])
    rut = cartera[0]["rut_empresa"]

    detalle = queries.obtener_detalle_empresa(rut)
    assert detalle is not None
    assert detalle["rut_empresa"] == rut
    assert "activos_banco_clp" in detalle
    assert "ventas_anuales_uf" in detalle
    assert "variacion_ventas_pct" in detalle


def test_cartera_ejecutivo_inexistente_retorna_lista_vacia():
    """Si el ejecutivo no existe, debe retornar lista vacia (no lanzar excepcion)."""
    cartera = queries.obtener_cartera_ejecutivo("Ejecutivo Inexistente XYZ")
    assert cartera == []
