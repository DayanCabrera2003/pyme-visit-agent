"""Tests de validacion de schemas Pydantic."""
import pytest
from models.schemas import (
    RankingItem,
    VisitaSeleccionada,
    BriefVisita,
    MetricasEmpresa,
    SessionState,
    EstadoSesion,
    IniciarSesionRequest,
    AprobacionRequest,
)


def test_ranking_item_valido():
    """RankingItem acepta datos validos."""
    item = RankingItem(
        rut_empresa="12.345.678-9",
        razon_social="Empresa Test S.A.",
        score_compuesto=75.5,
        justificacion="Score alto por campana vigente.",
        tags=["Campana activa", "Peak estacional"],
        aprobado=True,
        tipo_campana_vigente="Credito",
        tipo_oportunidad_principal="Credito",
        dias_desde_ultima_visita=45,
        share_of_wallet_pct=22.0,
        excedente_caja_uf=300.0,
        meses_sin_venta=0,
    )
    assert item.score_compuesto == 75.5
    assert item.aprobado is True


def test_ranking_item_score_fuera_de_rango():
    """RankingItem debe rechazar scores fuera del rango 0-100."""
    with pytest.raises(Exception):
        RankingItem(
            rut_empresa="1",
            razon_social="Test",
            score_compuesto=150.0,
            justificacion="",
            tags=[],
            aprobado=True,
            tipo_campana_vigente=None,
            tipo_oportunidad_principal="",
            dias_desde_ultima_visita=0,
            share_of_wallet_pct=0.0,
            excedente_caja_uf=0.0,
            meses_sin_venta=0,
        )


def test_visita_seleccionada_dia_valido():
    """VisitaSeleccionada acepta solo dias validos de la semana."""
    visita = VisitaSeleccionada(
        rut_empresa="1",
        razon_social="Test",
        dia_visita_sugerido="Lunes",
        tipo_oportunidad="Credito",
        producto_recomendado="Linea de credito",
        argumento_principal="El cliente tiene SoW bajo.",
        aprobado=True,
    )
    assert visita.dia_visita_sugerido == "Lunes"


def test_visita_seleccionada_dia_invalido():
    """VisitaSeleccionada debe rechazar dias que no son de la semana laboral."""
    with pytest.raises(Exception):
        VisitaSeleccionada(
            rut_empresa="1",
            razon_social="Test",
            dia_visita_sugerido="Domingo",
            tipo_oportunidad="Credito",
            producto_recomendado="",
            argumento_principal="",
            aprobado=True,
        )


def test_session_state_estado_inicial():
    """SessionState se crea con estado 'inicio' por defecto."""
    sesion = SessionState(
        session_id="abc-123",
        nombre_ejecutivo="Carlos Perez",
        sucursal="Providencia",
    )
    assert sesion.estado == EstadoSesion.INICIO
    assert sesion.cartera_completa == []
    assert sesion.ranking_aprobado == []
    assert sesion.briefs_finales == []


def test_aprobacion_request_acepta_lista_vacia():
    """AprobacionRequest acepta lista vacia de descartados (aprueba todo)."""
    req = AprobacionRequest(
        session_id="abc-123",
        elementos_descartados=[],
        comentario="Sin comentarios.",
    )
    assert req.elementos_descartados == []
