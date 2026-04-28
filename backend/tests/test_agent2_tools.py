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
    """guardar_visitas debe persistir en sesiones[session_id] con 5 visitas validas."""
    # Se usan 5 visitas distribuidas para cumplir las validaciones de negocio.
    items = [
        {
            "rut_empresa": "11.111.111-1",
            "razon_social": "Empresa A",
            "dia_visita_sugerido": "Lunes",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "Linea de credito",
            "argumento_principal": "SoW bajo.",
            "aprobado": True,
        },
        {
            "rut_empresa": "22.222.222-2",
            "razon_social": "Empresa B",
            "dia_visita_sugerido": "Martes",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "Linea de credito",
            "argumento_principal": "SoW bajo.",
        },
        {
            "rut_empresa": "33.333.333-3",
            "razon_social": "Empresa C",
            "dia_visita_sugerido": "Miercoles",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "Linea de credito",
            "argumento_principal": "SoW bajo.",
        },
        {
            "rut_empresa": "44.444.444-4",
            "razon_social": "Empresa D",
            "dia_visita_sugerido": "Jueves",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "Linea de credito",
            "argumento_principal": "SoW bajo.",
        },
        {
            "rut_empresa": "55.555.555-5",
            "razon_social": "Empresa E",
            "dia_visita_sugerido": "Viernes",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "Linea de credito",
            "argumento_principal": "SoW bajo.",
        },
    ]
    resultado = runner.guardar_visitas(items)
    assert "5" in resultado
    assert "visitas_seleccionadas" in sesiones["test-session"]
    assert len(sesiones["test-session"]["visitas_seleccionadas"]) == 5


def test_guardar_visitas_rechaza_dia_invalido(runner, sesiones):
    """guardar_visitas debe manejar gracefully un dia invalido."""
    # Se usan 5 items para superar la validacion de cantidad minima.
    # El primer item tiene dia invalido (Sabado), lo que debe generar error en el schema.
    items = [
        {
            "rut_empresa": "11.111.111-1",
            "razon_social": "Empresa A",
            "dia_visita_sugerido": "Sabado",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "...",
            "argumento_principal": "...",
            "aprobado": True,
        },
        {
            "rut_empresa": "22.222.222-2",
            "razon_social": "Empresa B",
            "dia_visita_sugerido": "Martes",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "...",
            "argumento_principal": "...",
        },
        {
            "rut_empresa": "33.333.333-3",
            "razon_social": "Empresa C",
            "dia_visita_sugerido": "Miercoles",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "...",
            "argumento_principal": "...",
        },
        {
            "rut_empresa": "44.444.444-4",
            "razon_social": "Empresa D",
            "dia_visita_sugerido": "Jueves",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "...",
            "argumento_principal": "...",
        },
        {
            "rut_empresa": "55.555.555-5",
            "razon_social": "Empresa E",
            "dia_visita_sugerido": "Viernes",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "...",
            "argumento_principal": "...",
        },
    ]
    resultado = runner.guardar_visitas(items)
    assert "Error" in resultado or "error" in resultado.lower()


def test_guardar_visitas_rechaza_menos_de_5(runner, sesiones):
    """guardar_visitas debe rechazar listas con menos de 5 visitas."""
    items = [
        {
            "rut_empresa": f"{i}.{i}.{i}-{i}",
            "razon_social": f"Empresa {i}",
            "dia_visita_sugerido": "Lunes",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "Linea",
            "argumento_principal": "Argumento.",
        }
        for i in range(1, 4)  # solo 3 visitas
    ]
    resultado = runner.guardar_visitas(items)
    assert "Error" in resultado
    assert "5" in resultado  # mensaje debe mencionar el minimo


def test_guardar_visitas_rechaza_mas_de_7(runner, sesiones):
    """guardar_visitas debe rechazar listas con mas de 7 visitas."""
    items = [
        {
            "rut_empresa": f"1{i}.111.111-{i}",
            "razon_social": f"Empresa {i}",
            "dia_visita_sugerido": "Lunes",
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "Linea",
            "argumento_principal": "Argumento.",
        }
        for i in range(8)  # 8 visitas
    ]
    resultado = runner.guardar_visitas(items)
    assert "Error" in resultado
    assert "7" in resultado


def test_guardar_visitas_rechaza_mas_de_2_por_dia(runner, sesiones):
    """guardar_visitas debe rechazar mas de 2 visitas el mismo dia."""
    dias = ["Lunes", "Lunes", "Lunes", "Martes", "Miercoles"]
    items = [
        {
            "rut_empresa": f"1{i}.111.111-{i}",
            "razon_social": f"Empresa {i}",
            "dia_visita_sugerido": dias[i],
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "Linea",
            "argumento_principal": "Argumento.",
        }
        for i in range(5)
    ]
    resultado = runner.guardar_visitas(items)
    assert "Error" in resultado
    assert "Lunes" in resultado


def test_guardar_visitas_acepta_5_distribuidas(runner, sesiones):
    """guardar_visitas debe aceptar exactamente 5 visitas bien distribuidas."""
    dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
    items = [
        {
            "rut_empresa": f"1{i}.111.111-{i}",
            "razon_social": f"Empresa {i}",
            "dia_visita_sugerido": dias[i],
            "tipo_oportunidad": "Credito",
            "producto_recomendado": "Linea",
            "argumento_principal": "Argumento.",
        }
        for i in range(5)
    ]
    resultado = runner.guardar_visitas(items)
    assert "Error" not in resultado
    assert "5" in resultado
