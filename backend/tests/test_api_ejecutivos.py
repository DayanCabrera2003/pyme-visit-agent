"""Tests del endpoint GET /ejecutivos."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_ejecutivos_retorna_lista():
    """GET /ejecutivos debe retornar lista de ejecutivos."""
    ejecutivos_mock = [
        {"nombre_ejecutivo": "Ana Garcia", "sucursal": "Las Condes", "regional": "RM"},
        {"nombre_ejecutivo": "Carlos Perez", "sucursal": "Providencia", "regional": "RM"},
    ]
    with patch("api.ejecutivos.queries.obtener_ejecutivos", return_value=ejecutivos_mock):
        response = client.get("/ejecutivos/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["nombre_ejecutivo"] == "Ana Garcia"


def test_get_ejecutivos_estructura_correcta():
    """Cada ejecutivo debe tener nombre, sucursal y regional."""
    ejecutivos_mock = [
        {"nombre_ejecutivo": "Test User", "sucursal": "Centro", "regional": "RM"}
    ]
    with patch("api.ejecutivos.queries.obtener_ejecutivos", return_value=ejecutivos_mock):
        response = client.get("/ejecutivos/")
    assert response.status_code == 200
    ejecutivo = response.json()[0]
    assert "nombre_ejecutivo" in ejecutivo
    assert "sucursal" in ejecutivo
    assert "regional" in ejecutivo


def test_get_ejecutivos_error_bd():
    """Si la BD falla, debe retornar 503."""
    with patch(
        "api.ejecutivos.queries.obtener_ejecutivos",
        side_effect=Exception("Connection refused")
    ):
        response = client.get("/ejecutivos/")
    assert response.status_code == 503
