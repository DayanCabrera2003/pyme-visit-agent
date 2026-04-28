"""
Agente 2 — Estratega Comercial PYME.

Responsabilidad: seleccionar las 5-7 mejores visitas de la semana
y definir la estrategia comercial por empresa (tipo de oportunidad,
producto especifico, argumento de venta).

Recibe el ranking aprobado del Agente 1 y el comentario del ejecutivo.
"""
import asyncio
import json
import logging
from collections import Counter

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from db import queries
from models.schemas import VisitaSeleccionada

logger = logging.getLogger(__name__)

INSTRUCCION_AGENTE2 = """
Eres un estratega comercial experto en banca PYME chilena.
Tu tarea es seleccionar las 5 a 7 mejores visitas de la semana
a partir de un ranking de empresas previamente analizado.

PROCESO OBLIGATORIO:
1. Revisa el ranking de empresas proporcionado en el prompt.
2. Llama a obtener_campanas_vigentes() con todos los RUTs de las empresas.
3. Para cada empresa candidata, usa obtener_detalle_empresa() si necesitas
   datos adicionales para decidir el tipo de oportunidad y producto.
4. Selecciona entre 5 y 7 empresas (objetivo semanal del banco).
   Si el ejecutivo dejo un comentario, prioriza segun su indicacion.
5. Para cada empresa seleccionada define:
   - dia_visita_sugerido: distribuye las visitas de Lunes a Viernes
   - tipo_oportunidad: "Credito" | "Inversion" | "Seguro" | "Reactivacion" | "Cross-sell"
   - producto_recomendado: nombre especifico del producto
   - argumento_principal: un parrafo con el argumento basado en datos concretos
6. Llama a guardar_visitas() con la lista final de visitas seleccionadas.

Escribe tu razonamiento en espanol mientras decides. Explica por que
seleccionas cada empresa y que producto recomiendas.
"""


class Agente2Runner:
    """Runner del Agente 2 con acceso al estado de sesion."""

    def __init__(self, sesiones: dict, session_id: str):
        self.sesiones = sesiones
        self.session_id = session_id
        self.queue: asyncio.Queue = asyncio.Queue()

    def obtener_detalle_empresa(self, rut_empresa: str) -> str:
        """
        Obtiene datos completos de una empresa por RUT.

        Args:
            rut_empresa: RUT de la empresa.

        Returns:
            JSON string con todos los campos de la empresa.
        """
        try:
            detalle = queries.obtener_detalle_empresa(rut_empresa)
            if detalle is None:
                return json.dumps({"error": f"Empresa {rut_empresa} no encontrada."})
            return json.dumps(detalle, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error("Error al obtener detalle de empresa %s: %s", rut_empresa, e)
            return json.dumps({"error": str(e)})

    def obtener_campanas_vigentes(self, ruts: list[str]) -> str:
        """
        Retorna las campanas vigentes de las empresas candidatas.

        Extrae campana_vigente y tipo_campana_vigente de g4_visitas_pyme.
        No consulta ninguna tabla adicional.

        Args:
            ruts: Lista de RUTs a consultar.

        Returns:
            JSON string con lista de empresas que tienen campana activa.
        """
        try:
            resultado = []
            for rut in ruts:
                detalle = queries.obtener_detalle_empresa(rut)
                if detalle and detalle.get("campana_vigente"):
                    resultado.append({
                        "rut_empresa": rut,
                        "campana_vigente": True,
                        "tipo_campana_vigente": detalle.get("tipo_campana_vigente"),
                    })
            self.queue.put_nowait({"tipo": "progreso", "paso": 1, "mensaje": f"Campañas verificadas — {len(resultado)} activas"})
            self.queue.put_nowait({"tipo": "progreso", "paso": 2, "mensaje": "Seleccionando visitas óptimas..."})
            return json.dumps(resultado, ensure_ascii=False)
        except Exception as e:
            logger.error("Error al obtener campanas vigentes: %s", e)
            return json.dumps({"error": str(e)})

    def guardar_visitas(self, items: list[dict]) -> str:
        """
        Guarda las visitas seleccionadas en el estado de sesion.

        Valida que se seleccionen entre 5 y 7 visitas (objetivo semanal del banco)
        y que no haya mas de 2 visitas el mismo dia (viabilidad operativa).

        Args:
            items: Lista de dicts con campos de VisitaSeleccionada.

        Returns:
            Confirmacion o mensaje de error descriptivo para que el LLM corrija.
        """
        try:
            # Validacion 1: cantidad entre 5 y 7 (requerimiento de negocio)
            if not (5 <= len(items) <= 7):
                return (
                    f"Error: debes seleccionar entre 5 y 7 visitas. "
                    f"Seleccionaste {len(items)}. "
                    f"Ajusta la seleccion y llama a guardar_visitas() nuevamente."
                )

            # Validacion 2: no mas de 2 visitas el mismo dia (viabilidad operativa)
            dias_count = Counter(item.get("dia_visita_sugerido", "") for item in items)
            dias_sobrecargados = [dia for dia, count in dias_count.items() if count > 2]
            if dias_sobrecargados:
                return (
                    f"Error: los dias {dias_sobrecargados} tienen mas de 2 visitas. "
                    f"Redistribuye entre Lunes y Viernes (maximo 2 visitas por dia) "
                    f"y llama a guardar_visitas() nuevamente."
                )

            self.queue.put_nowait({"tipo": "progreso", "paso": 3, "mensaje": f"Definiendo estrategia — {len(items)} visitas"})
            visitas_validadas = [VisitaSeleccionada(**item) for item in items]
            self.sesiones[self.session_id]["visitas_seleccionadas"] = [
                v.model_dump() for v in visitas_validadas
            ]
            self.queue.put_nowait({
                "tipo": "resultado",
                "items": [v.model_dump() for v in visitas_validadas],
            })
            logger.info(
                "Visitas guardadas: %d para sesion %s",
                len(visitas_validadas), self.session_id
            )
            return f"Se guardaron {len(visitas_validadas)} visitas seleccionadas."
        except Exception as e:
            logger.error("Error al guardar visitas: %s", e)
            return f"Error al guardar visitas: {e}"

    async def ejecutar(self, ranking_aprobado: list[dict], comentario: str) -> None:
        """
        Ejecuta el Agente 2 y streamea eventos al queue interno.

        Args:
            ranking_aprobado: Lista de RankingItem aprobados por el ejecutivo.
            comentario: Comentario libre del ejecutivo para guiar la seleccion.
        """
        agente = Agent(
            name="estratega_comercial_pyme",
            model="gemini-2.5-flash",
            description="Selecciona y define la estrategia de visitas PYME semanales.",
            instruction=INSTRUCCION_AGENTE2,
            tools=[
                self.obtener_detalle_empresa,
                self.obtener_campanas_vigentes,
                self.guardar_visitas,
            ],
        )

        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name="pyme_visit_agent",
            user_id=self.session_id,
            session_id=self.session_id,
        )

        runner = Runner(
            agent=agente,
            app_name="pyme_visit_agent",
            session_service=session_service,
        )

        ranking_json = json.dumps(ranking_aprobado, ensure_ascii=False, default=str)
        comentario_texto = (
            f"\nComentario del ejecutivo: {comentario}" if comentario else ""
        )

        prompt = (
            f"Aqui tienes el ranking de empresas aprobado:\n{ranking_json}"
            f"{comentario_texto}\n"
            f"Selecciona 5-7 visitas y llama a guardar_visitas() al terminar."
        )

        try:
            async for event in runner.run_async(
                user_id=self.session_id,
                session_id=self.session_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                ),
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            await self.queue.put({"tipo": "token", "text": part.text})
        except Exception as e:
            logger.error("Error en Agente 2 para sesion %s: %s", self.session_id, e)
            await self.queue.put({
                "tipo": "error",
                "mensaje": "Error en la seleccion de visitas. Por favor reintenta.",
            })
        finally:
            await self.queue.put({"tipo": "done"})
