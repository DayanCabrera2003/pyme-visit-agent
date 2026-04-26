"""Tests de endpoints de aprobacion de agentes (no testea SSE directamente)."""
import time
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app
from models.schemas import RankingItem, EstadoSesion

client = TestClient(app)


def _crear_sesion_en_store(session_id: str, estado: str, datos: dict = None):
    """Helper: inyecta una sesion en el store directamente para tests."""
    from sesiones_store import SESIONES
    SESIONES[session_id] = {
        "session_id": session_id,
        "nombre_ejecutivo": "Test Ejecutivo",
        "sucursal": "Test Sucursal",
        "estado": estado,
        "created_at": time.time(),
        "cartera_completa": [],
        "ranking_aprobado": [],
        "comentario_1": "",
        "visitas_seleccionadas": [],
        "comentario_2": "",
        "briefs_finales": [],
        **(datos or {}),
    }


def test_approve_agente1_filtra_descartados():
    """POST /agent/1/approve debe filtrar empresas descartadas del ranking."""
    session_id = "test-approve-1"
    cartera = [
        {
            "rut_empresa": "1.1", "razon_social": "A", "score_compuesto": 80,
            "justificacion": "ok", "tags": [], "aprobado": True,
            "tipo_campana_vigente": None, "tipo_oportunidad_principal": "Credito",
            "dias_desde_ultima_visita": 30, "share_of_wallet_pct": 20.0,
            "excedente_caja_uf": 100.0, "meses_sin_venta": 0,
        },
        {
            "rut_empresa": "2.2", "razon_social": "B", "score_compuesto": 60,
            "justificacion": "ok", "tags": [], "aprobado": True,
            "tipo_campana_vigente": None, "tipo_oportunidad_principal": "Seguro",
            "dias_desde_ultima_visita": 10, "share_of_wallet_pct": 50.0,
            "excedente_caja_uf": 0.0, "meses_sin_venta": 0,
        },
    ]
    _crear_sesion_en_store(
        session_id,
        "agente1_pendiente_aprobacion",
        {"cartera_completa": cartera},
    )

    response = client.post("/agent/1/approve", json={
        "session_id": session_id,
        "elementos_descartados": ["2.2"],
        "comentario": "",
    })
    assert response.status_code == 200

    from sesiones_store import SESIONES
    ranking = SESIONES[session_id]["ranking_aprobado"]
    assert len(ranking) == 1
    assert ranking[0]["rut_empresa"] == "1.1"


def test_approve_agente1_sesion_inexistente():
    """POST /agent/1/approve con sesion invalida retorna 410."""
    response = client.post("/agent/1/approve", json={
        "session_id": "no-existe",
        "elementos_descartados": [],
        "comentario": "",
    })
    assert response.status_code == 410


def test_approve_agente2_filtra_descartados():
    """POST /agent/2/approve filtra visitas descartadas."""
    session_id = "test-approve-2"
    visitas = [
        {
            "rut_empresa": "1.1", "razon_social": "A",
            "dia_visita_sugerido": "Lunes", "tipo_oportunidad": "Credito",
            "producto_recomendado": "Linea", "argumento_principal": "ok",
            "aprobado": True,
        },
        {
            "rut_empresa": "2.2", "razon_social": "B",
            "dia_visita_sugerido": "Martes", "tipo_oportunidad": "Seguro",
            "producto_recomendado": "Seguro", "argumento_principal": "ok",
            "aprobado": True,
        },
    ]
    _crear_sesion_en_store(
        session_id,
        "agente2_pendiente_aprobacion",
        {"visitas_seleccionadas": visitas},
    )

    response = client.post("/agent/2/approve", json={
        "session_id": session_id,
        "elementos_descartados": ["2.2"],
        "comentario": "Priorizar credito esta semana.",
    })
    assert response.status_code == 200
    from sesiones_store import SESIONES
    visitas_ok = SESIONES[session_id]["visitas_seleccionadas"]
    assert len(visitas_ok) == 1
    assert SESIONES[session_id]["comentario_2"] == "Priorizar credito esta semana."
