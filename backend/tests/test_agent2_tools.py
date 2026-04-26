"""Tests de las tools del Agente 2."""
import json
import pytest
from unittest.mock import patch, MagicMock
from agents.agent2_estratega import Agente2Runner
from models.schemas import RankingItem


@pytest.fixture
def sesiones():
    """Estado de sesion con ranking aprobado de prueba."""
    ranking = [
        RankingItem(
            rut_empresa="11.111.111-1",
            razon_social="Empresa A",
            score_compuesto=85.0,
            justificacion="Score alto.",
            tags=["Campana activa: Credito"],
            aprobado=True,
            tipo_campana_vigente="Credito",
            tipo_oportunidad_principal="Credito",
            dias_desde_ultima_visita=60,
            share_of_wallet_pct=20.0,
            excedente_caja_uf=400.0,
            meses_sin_venta=0,
        ),
        RankingItem(
            rut_empresa="22.222.222-2",
            razon_social="Empresa B",
            score_compuesto=70.0,
            justificacion="Score medio.",
            tags=["Sin venta: 5 meses"],
            aprobado=True,
            tipo_campana_vigente=None,
            tipo_oportunidad_principal="Reactivacion",
            dias_desde_ultima_visita=90,
            share_of_wallet_pct=50.0,
            excedente_caja_uf=0.0,
            meses_sin_venta=5,
        ),
    ]
    return {
        "test-session": {
            "nombre_ejecutivo": "Carlos Perez",
            "ranking_aprobado": [r.model_dump() for r in ranking],
            "comentario_1": "",
        }
    }


@pytest.fixture
def runner(sesiones):
    return Agente2Runner(sesiones=sesiones, session_id="test-session")


def test_obtener_campanas_vigentes_solo_las_que_tienen(runner, sesiones):
    """Solo retorna empresas que efectivamente tienen campana vigente."""
    with patch("agents.agent2_estratega.queries.obtener_detalle_empresa") as mock:
        mock.side_effect = lambda rut: {
            "rut_empresa": rut,
            "campana_vigente": rut == "11.111.111-1",
            "tipo_campana_vigente": "Credito" if rut == "11.111.111-1" else None,
        }
        resultado = runner.obtener_campanas_vigentes(
            ["11.111.111-1", "22.222.222-2"]
        )
    data = json.loads(resultado)
    assert len(data) == 1
    assert data[0]["rut_empresa"] == "11.111.111-1"


def test_guardar_visitas_persiste_en_sesion(runner, sesiones):
    """guardar_visitas debe persistir en sesiones[session_id]."""
    items = [
        {
            "rut_empresa": "11.111.111-1",
            "razon_social": "Empresa A",
            "dia_visita_sugerido": "Lunes",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "Linea de credito",
            "argumento_principal": "SoW bajo.",
            "aprobado": True,
        }
    ]
    resultado = runner.guardar_visitas(items)
    assert "1" in resultado
    assert "visitas_seleccionadas" in sesiones["test-session"]
    assert len(sesiones["test-session"]["visitas_seleccionadas"]) == 1


def test_guardar_visitas_rechaza_dia_invalido(runner, sesiones):
    """guardar_visitas debe manejar gracefully un dia invalido."""
    items = [
        {
            "rut_empresa": "11.111.111-1",
            "razon_social": "Empresa A",
            "dia_visita_sugerido": "Sabado",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "...",
            "argumento_principal": "...",
            "aprobado": True,
        }
    ]
    resultado = runner.guardar_visitas(items)
    assert "Error" in resultado or "error" in resultado.lower()
