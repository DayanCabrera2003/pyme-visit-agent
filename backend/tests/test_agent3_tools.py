"""Tests de las tools del Agente 3."""
import pytest
from unittest.mock import patch
from agents.agent3_briefs import Agente3Runner
from models.schemas import VisitaSeleccionada


@pytest.fixture
def sesiones():
    visitas = [
        VisitaSeleccionada(
            rut_empresa="11.111.111-1",
            razon_social="Empresa A",
            dia_visita_sugerido="Lunes",
            tipo_oportunidad="Credito",
            producto_recomendado="Linea de credito rotativa",
            argumento_principal="SoW del 18% con potencial de crecimiento.",
            aprobado=True,
        )
    ]
    return {
        "test-session": {
            "visitas_seleccionadas": [v.model_dump() for v in visitas],
            "comentario_2": "",
        }
    }


@pytest.fixture
def runner(sesiones):
    return Agente3Runner(sesiones=sesiones, session_id="test-session")


def test_guardar_briefs_persiste_en_sesion(runner, sesiones):
    """guardar_briefs debe persistir en sesiones[session_id]."""
    briefs = [
        {
            "rut_empresa": "11.111.111-1",
            "razon_social": "Empresa A",
            "rubro": "Construccion",
            "direccion": "Av. Principal 123",
            "dia_visita": "Lunes",
            "score_compuesto": 85.0,
            "tags": ["Campana activa"],
            # Campos societarios requeridos por BriefVisita
            "n_socios": 1,
            "nombre_socio_principal": "Ana Lopez",
            "tiene_empresas_relacionadas": False,
            "metricas": {
                "activos_banco_clp": 4000000000,
                "activos_industria_clp": 10000000000,
                "share_of_wallet_pct": 40.0,
                "ventas_anuales_uf": 2800.0,
                "variacion_ventas_pct": 12.0,
                "meses_sin_venta": 0,
                "excedente_caja_uf": 100.0,
                "inversiones_uf": 50.0,
                "costos_financieros_uf": 30.0,
                "dias_desde_ultima_visita": 42,
            },
            "oportunidad": "Hay oportunidad de credito dado el SoW bajo.",
            "preguntas_sugeridas": [
                "Tienen proyectos de expansion planificados?",
                "Como manejan el excedente de caja?",
            ],
        }
    ]
    resultado = runner.guardar_briefs(briefs)
    assert "1" in resultado
    assert "briefs_finales" in sesiones["test-session"]
    assert len(sesiones["test-session"]["briefs_finales"]) == 1


def test_guardar_briefs_maneja_datos_invalidos(runner, sesiones):
    """guardar_briefs no debe lanzar excepcion con datos incompletos."""
    resultado = runner.guardar_briefs([{"rut_empresa": "1"}])
    assert "Error" in resultado or "error" in resultado.lower()


def test_guardar_briefs_enriquece_con_campos_financieros_completos(runner, sesiones):
    """guardar_briefs debe rellenar campos financieros y maya societaria desde BD."""
    detalle_bd = {
        "rut_empresa": "11.111.111-1",
        "razon_social": "Empresa A",
        "rubro": "Comercio",
        "direccion": "Calle 1",
        "score_oportunidad": 78.5,
        "activos_banco_clp": 5_000_000_000,
        "activos_industria_clp": 20_000_000_000,
        "share_of_wallet_pct": 25.0,
        "ventas_anuales_uf": 1200.0,
        "variacion_ventas_pct": 8.5,
        "meses_sin_venta": 0,
        "excedente_caja_uf": 150.0,
        "inversiones_uf": 200.0,
        "costos_financieros_uf": 80.0,
        "dias_desde_ultima_visita": 45,
        "n_socios": 2,
        "nombre_socio_principal": "Juan Perez",
        "tiene_empresas_relacionadas": False,
    }
    with patch("agents.agent3_briefs.queries.obtener_detalle_empresa", return_value=detalle_bd):
        # Brief minimo: solo lo que el LLM suele enviar
        briefs = [{
            "rut_empresa": "11.111.111-1",
            "oportunidad": "Oportunidad de credito.",
            "preguntas_sugeridas": ["Pregunta 1?", "Pregunta 2?"],
        }]
        runner._visitas = [{"rut_empresa": "11.111.111-1", "dia_visita_sugerido": "Martes"}]
        resultado = runner.guardar_briefs(briefs)

    assert "Error" not in resultado
    brief_final = sesiones["test-session"]["briefs_finales"][0]
    metricas = brief_final["metricas"]
    assert metricas["activos_industria_clp"] == 20_000_000_000
    assert metricas["inversiones_uf"] == 200.0
    assert metricas["costos_financieros_uf"] == 80.0
    assert brief_final["n_socios"] == 2
    assert brief_final["nombre_socio_principal"] == "Juan Perez"
