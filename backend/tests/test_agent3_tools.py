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
            "metricas": {
                "activos_banco_clp": 4000000000,
                "ventas_anuales_uf": 2800.0,
                "variacion_ventas_pct": 12.0,
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
