"""
Capa de acceso a datos — queries SQL a g4_visitas_pyme.

Este modulo solo contiene logica de acceso a datos.
No tiene logica de negocio ni calculo de scores.
Toda query usa parametros preparados para evitar SQL injection.
"""
import logging
from typing import Optional

from db.connection import obtener_conexion

logger = logging.getLogger(__name__)


def obtener_ejecutivos() -> list[dict]:
    """
    Retorna la lista de ejecutivos unicos con su sucursal y regional.

    Retorna:
        Lista de dicts con keys: nombre_ejecutivo, sucursal, regional.
        Lista vacia si no hay datos.
    """
    sql = """
        SELECT DISTINCT
            nombre_ejecutivo,
            sucursal,
            regional
        FROM g4_visitas_pyme
        WHERE nombre_ejecutivo IS NOT NULL
        ORDER BY nombre_ejecutivo
    """
    with obtener_conexion() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        columnas = [desc[0] for desc in cur.description]
        filas = cur.fetchall()
        return [dict(zip(columnas, fila)) for fila in filas]


def obtener_cartera_ejecutivo(nombre_ejecutivo: str) -> list[dict]:
    """
    Retorna todas las empresas de la cartera de un ejecutivo.

    Incluye todos los campos necesarios para el scoring del Agente 1
    y la estrategia del Agente 2, evitando queries adicionales.

    Args:
        nombre_ejecutivo: Nombre exacto del ejecutivo segun la BD.

    Retorna:
        Lista de dicts con datos de cada empresa. Lista vacia si el ejecutivo
        no existe o no tiene empresas asignadas.
    """
    sql = """
        SELECT
            id,
            rut_empresa,
            razon_social,
            direccion,
            rubro,
            industria,
            nombre_socio_principal,
            n_socios,
            tiene_empresas_relacionadas,
            n_productos_activos,
            productos_activos_detalle,
            activos_banco_clp,
            activos_industria_clp,
            share_of_wallet_pct,
            campana_vigente,
            tipo_campana_vigente,
            fecha_ultima_visita,
            dias_desde_ultima_visita,
            resultado_ultima_visita,
            ventas_anuales_uf,
            variacion_ventas_pct,
            meses_sin_venta,
            excedente_caja_uf,
            inversiones_uf,
            costos_financieros_uf,
            n_empleados,
            estacionalidad,
            mes_peak_negocio,
            tipo_oportunidad_principal,
            score_oportunidad,
            sucursal,
            regional
        FROM g4_visitas_pyme
        WHERE nombre_ejecutivo = %s
        ORDER BY score_oportunidad DESC
    """
    with obtener_conexion() as conn:
        cur = conn.cursor()
        cur.execute(sql, (nombre_ejecutivo,))
        columnas = [desc[0] for desc in cur.description]
        filas = cur.fetchall()
        return [dict(zip(columnas, fila)) for fila in filas]


def obtener_detalle_empresa(rut_empresa: str) -> Optional[dict]:
    """
    Retorna el detalle completo de una empresa por su RUT.

    Args:
        rut_empresa: RUT de la empresa.

    Retorna:
        Dict con todos los campos de la empresa, o None si no existe.
    """
    sql = """
        SELECT *
        FROM g4_visitas_pyme
        WHERE rut_empresa = %s
        LIMIT 1
    """
    with obtener_conexion() as conn:
        cur = conn.cursor()
        cur.execute(sql, (rut_empresa,))
        columnas = [desc[0] for desc in cur.description]
        fila = cur.fetchone()
        if fila is None:
            return None
        return dict(zip(columnas, fila))
