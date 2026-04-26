"""
Schemas Pydantic — contratos de datos entre agentes y la API.

Cada schema tiene una responsabilidad clara:
- RankingItem: output del Agente 1, input del Agente 2
- VisitaSeleccionada: output del Agente 2, input del Agente 3
- BriefVisita: output del Agente 3, contenido del PDF
- SessionState: estado completo de una sesion de usuario
- Request/Response: contratos de los endpoints de la API
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# Dias validos de la semana laboral bancaria
DIAS_SEMANA = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]


class EstadoSesion(str, Enum):
    """Estados posibles de una sesion, cubren ejecucion y espera por separado."""
    INICIO = "inicio"
    AGENTE1_EJECUTANDO = "agente1_ejecutando"
    AGENTE1_PENDIENTE = "agente1_pendiente_aprobacion"
    AGENTE2_EJECUTANDO = "agente2_ejecutando"
    AGENTE2_PENDIENTE = "agente2_pendiente_aprobacion"
    AGENTE3_EJECUTANDO = "agente3_ejecutando"
    COMPLETO = "completo"


class RankingItem(BaseModel):
    """
    Un item del ranking producido por el Agente 1.

    Incluye campos raw de la BD para que el Agente 2
    no necesite consultar la BD nuevamente.
    """
    rut_empresa: str
    razon_social: str
    score_compuesto: float = Field(ge=0.0, le=100.0)
    justificacion: str
    tags: list[str] = []
    aprobado: bool = True
    # Campos raw de BD para el Agente 2
    tipo_campana_vigente: Optional[str] = None
    tipo_oportunidad_principal: Optional[str] = None
    dias_desde_ultima_visita: int = 0
    share_of_wallet_pct: float = 0.0
    excedente_caja_uf: float = 0.0
    meses_sin_venta: int = 0


class VisitaSeleccionada(BaseModel):
    """Un item de la shortlist producida por el Agente 2 (5-7 visitas)."""
    rut_empresa: str
    razon_social: str
    dia_visita_sugerido: str
    tipo_oportunidad: str
    producto_recomendado: str
    argumento_principal: str
    aprobado: bool = True

    @field_validator("dia_visita_sugerido")
    @classmethod
    def validar_dia(cls, v: str) -> str:
        """Solo acepta dias de la semana laboral."""
        if v not in DIAS_SEMANA:
            raise ValueError(
                f"'{v}' no es un dia valido. Usar: {', '.join(DIAS_SEMANA)}"
            )
        return v


class MetricasEmpresa(BaseModel):
    """Metricas financieras clave de una empresa para el brief."""
    activos_banco_clp: int = 0
    ventas_anuales_uf: float = 0.0
    variacion_ventas_pct: float = 0.0
    dias_desde_ultima_visita: int = 0


class BriefVisita(BaseModel):
    """Brief comercial completo generado por el Agente 3 para una visita."""
    rut_empresa: str
    razon_social: str
    rubro: str
    direccion: str
    dia_visita: str
    score_compuesto: float
    tags: list[str] = []
    metricas: MetricasEmpresa
    oportunidad: str
    preguntas_sugeridas: list[str] = []


class SessionState(BaseModel):
    """Estado completo de una sesion de usuario en memoria."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre_ejecutivo: str
    sucursal: str
    estado: EstadoSesion = EstadoSesion.INICIO
    created_at: float = Field(default_factory=time.time)
    # Datos por etapa
    cartera_completa: list[RankingItem] = []
    ranking_aprobado: list[RankingItem] = []
    comentario_1: str = ""
    visitas_seleccionadas: list[VisitaSeleccionada] = []
    comentario_2: str = ""
    briefs_finales: list[BriefVisita] = []


# --- Request/Response de la API ---

class IniciarSesionRequest(BaseModel):
    """Body de POST /session/start."""
    nombre_ejecutivo: str


class IniciarSesionResponse(BaseModel):
    """Response de POST /session/start."""
    session_id: str
    nombre_ejecutivo: str
    sucursal: str
    n_empresas_cartera: int


class AprobacionRequest(BaseModel):
    """Body de POST /agent/{n}/approve."""
    session_id: str
    # Lista de RUTs (agente 1) o RUTs (agente 2) que el usuario descarto
    elementos_descartados: list[str] = []
    comentario: str = ""


class EjecutivoResponse(BaseModel):
    """Un ejecutivo en el listado de GET /ejecutivos."""
    nombre_ejecutivo: str
    sucursal: str
    regional: str
