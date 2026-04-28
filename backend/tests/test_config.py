"""Tests de configuracion — verifica lectura de variables de entorno."""
import sys
import importlib
from unittest.mock import patch
import pytest


def _reimportar_config():
    """
    Elimina el modulo del cache y lo reimporta para forzar relectura del entorno.

    load_dotenv se mockea como no-op para que los valores del .env real no
    sobreescriban las variables que monkeypatch acaba de modificar.
    """
    for key in list(sys.modules.keys()):
        if key == "config" or key == "backend.config":
            del sys.modules[key]
    # load_dotenv no-op: evita que el .env real restaure las vars eliminadas
    with patch("dotenv.load_dotenv"):
        return importlib.import_module("config")


def test_config_falla_sin_gemini_api_key(monkeypatch):
    """Config debe lanzar excepcion si GEMINI_API_KEY no esta definida."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        _reimportar_config()


def test_config_falla_sin_database_url(monkeypatch):
    """Config debe lanzar excepcion si DATABASE_URL no esta definida."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="DATABASE_URL"):
        _reimportar_config()


def test_config_carga_valores(monkeypatch):
    """Config retorna valores correctos cuando las variables estan presentes."""
    monkeypatch.setenv("GEMINI_API_KEY", "mi-api-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setenv("SESSION_TTL_MINUTES", "30")

    cfg = _reimportar_config()

    assert cfg.GEMINI_API_KEY == "mi-api-key"
    assert cfg.DATABASE_URL == "postgresql://user:pass@host/db"
    assert cfg.SESSION_TTL_MINUTES == 30
