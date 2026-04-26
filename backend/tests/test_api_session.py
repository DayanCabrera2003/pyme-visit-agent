"""Tests de endpoints de sesion."""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_iniciar_sesion_ejecutivo_valido():
    """POST /session/start con ejecutivo valido retorna session_id."""
    cartera_mock = [
        {
            "rut_empresa": "1.1", "razon_social": "Empresa A",
            "sucursal": "Las Condes",
            "score_oportunidad": 80, "dias_desde_ultima_visita": 30,
            "campana_vigente": True, "mes_peak_negocio": "abril",
            "share_of_wallet_pct": 20.0, "meses_sin_venta": 0,
        }
    ]
    ejecutivos_mock = [
        {"nombre_ejecutivo": "Ana Garcia", "sucursal": "Las Condes", "regional": "RM"}
    ]
    with patch("api.session.queries.obtener_ejecutivos", return_value=ejecutivos_mock), \
         patch("api.session.queries.obtener_cartera_ejecutivo", return_value=cartera_mock):
        response = client.post("/session/start", json={"nombre_ejecutivo": "Ana Garcia"})

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["nombre_ejecutivo"] == "Ana Garcia"
    assert data["n_empresas_cartera"] == 1


def test_iniciar_sesion_ejecutivo_inexistente():
    """POST /session/start con ejecutivo inexistente retorna 404."""
    with patch("api.session.queries.obtener_ejecutivos", return_value=[]), \
         patch("api.session.queries.obtener_cartera_ejecutivo", return_value=[]):
        response = client.post(
            "/session/start", json={"nombre_ejecutivo": "Nadie Aqui"}
        )
    assert response.status_code == 404


def test_obtener_sesion_existente():
    """GET /session/{id} retorna estado de sesion activa."""
    cartera_mock = [
        {
            "rut_empresa": "1.1", "razon_social": "B",
            "sucursal": "Providencia",
            "score_oportunidad": 70, "dias_desde_ultima_visita": 20,
            "campana_vigente": False, "mes_peak_negocio": "mayo",
            "share_of_wallet_pct": 40.0, "meses_sin_venta": 1,
        }
    ]
    ejecutivos_mock = [
        {"nombre_ejecutivo": "Carlos P.", "sucursal": "Providencia", "regional": "RM"}
    ]
    with patch("api.session.queries.obtener_ejecutivos", return_value=ejecutivos_mock), \
         patch("api.session.queries.obtener_cartera_ejecutivo", return_value=cartera_mock):
        create_resp = client.post("/session/start", json={"nombre_ejecutivo": "Carlos P."})

    session_id = create_resp.json()["session_id"]
    get_resp = client.get(f"/session/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["estado"] == "inicio"


def test_obtener_sesion_inexistente():
    """GET /session/{id} con id invalido retorna 410."""
    response = client.get("/session/no-existe-este-id-abc123")
    assert response.status_code == 410
