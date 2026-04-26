"""
Tests de las tools del Agente 1.

No se testea el LLM directamente (no determinista).
Se testean las funciones de calculo de score y obtencion de datos,
que son deterministas y tienen logica de negocio verificable.
"""
import pytest
from unittest.mock import patch, MagicMock
from agents.agent1_analista import Agente1Runner


@pytest.fixture
def runner():
    """Instancia del runner con sesiones mockeadas."""
    sesiones = {}
    return Agente1Runner(sesiones=sesiones, session_id="test-session")


def test_calcular_score_campana_vigente(runner):
    """Empresa con campana vigente recibe bonus de 15 puntos."""
    empresa = {
        "score_oportunidad": 50,
        "dias_desde_ultima_visita": 30,
        "campana_vigente": True,
        "mes_peak_negocio": "diciembre",
        "share_of_wallet_pct": 50.0,
        "meses_sin_venta": 0,
    }
    score = runner.calcular_score(empresa, mes_actual="abril")
    # 0.30*50 + 0.20*(30/90)*100 + 15 = 15 + 6.67 + 15 = ~36.67
    assert score > 30


def test_calcular_score_sin_campana(runner):
    """Empresa sin campana no recibe bonus de campana."""
    empresa = {
        "score_oportunidad": 50,
        "dias_desde_ultima_visita": 30,
        "campana_vigente": False,
        "mes_peak_negocio": "diciembre",
        "share_of_wallet_pct": 50.0,
        "meses_sin_venta": 0,
    }
    score_sin = runner.calcular_score(empresa, mes_actual="abril")

    empresa["campana_vigente"] = True
    score_con = runner.calcular_score(empresa, mes_actual="abril")

    assert score_con - score_sin == pytest.approx(15.0, abs=0.1)


def test_calcular_score_estacionalidad_mes_actual(runner):
    """Empresa con peak en el mes actual recibe bonus de estacionalidad."""
    empresa = {
        "score_oportunidad": 50,
        "dias_desde_ultima_visita": 30,
        "campana_vigente": False,
        "mes_peak_negocio": "abril",
        "share_of_wallet_pct": 50.0,
        "meses_sin_venta": 0,
    }
    score = runner.calcular_score(empresa, mes_actual="abril")
    assert score > 20


def test_calcular_score_sow_bajo(runner):
    """SoW < 30% agrega 10 puntos de oportunidad de crecimiento."""
    empresa_sow_bajo = {
        "score_oportunidad": 50, "dias_desde_ultima_visita": 30,
        "campana_vigente": False, "mes_peak_negocio": "diciembre",
        "share_of_wallet_pct": 15.0, "meses_sin_venta": 0,
    }
    empresa_sow_alto = dict(empresa_sow_bajo)
    empresa_sow_alto["share_of_wallet_pct"] = 60.0

    score_bajo = runner.calcular_score(empresa_sow_bajo, mes_actual="abril")
    score_alto = runner.calcular_score(empresa_sow_alto, mes_actual="abril")
    assert score_bajo - score_alto == pytest.approx(10.0, abs=0.1)


def test_calcular_score_riesgo_perdida(runner):
    """Empresa con mas de 3 meses sin venta recibe 10 puntos de riesgo."""
    empresa = {
        "score_oportunidad": 50, "dias_desde_ultima_visita": 30,
        "campana_vigente": False, "mes_peak_negocio": "diciembre",
        "share_of_wallet_pct": 50.0, "meses_sin_venta": 5,
    }
    score_con_riesgo = runner.calcular_score(empresa, mes_actual="abril")

    empresa["meses_sin_venta"] = 1
    score_sin_riesgo = runner.calcular_score(empresa, mes_actual="abril")

    assert score_con_riesgo - score_sin_riesgo == pytest.approx(10.0, abs=0.1)


def test_calcular_score_maximo_100(runner):
    """El score compuesto nunca supera 100."""
    empresa = {
        "score_oportunidad": 100,
        "dias_desde_ultima_visita": 180,
        "campana_vigente": True,
        "mes_peak_negocio": "abril",
        "share_of_wallet_pct": 5.0,
        "meses_sin_venta": 6,
    }
    score = runner.calcular_score(empresa, mes_actual="abril")
    assert score <= 100.0


def test_construir_tags_campana(runner):
    """Empresa con campana vigente recibe tag de campana."""
    empresa = {
        "campana_vigente": True,
        "tipo_campana_vigente": "Credito",
        "meses_sin_venta": 0,
        "mes_peak_negocio": "diciembre",
        "share_of_wallet_pct": 50.0,
    }
    tags = runner.construir_tags(empresa, mes_actual="abril")
    assert "Campaña activa: Credito" in tags


def test_construir_tags_sin_venta(runner):
    """Empresa con meses sin venta recibe tag de alerta."""
    empresa = {
        "campana_vigente": False,
        "tipo_campana_vigente": None,
        "meses_sin_venta": 4,
        "mes_peak_negocio": "diciembre",
        "share_of_wallet_pct": 50.0,
    }
    tags = runner.construir_tags(empresa, mes_actual="abril")
    assert any("4 meses" in t for t in tags)
