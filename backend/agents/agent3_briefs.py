"""
Agente 3 — Generador de Briefs Comerciales PYME.

Responsabilidad: generar un brief comercial completo y accionable
por cada empresa de la shortlist aprobada por el ejecutivo.

El brief incluye: resumen del cliente, situacion financiera,
oportunidad identificada, argumento comercial y preguntas sugeridas.
"""
import asyncio
import json
import logging

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from db import queries
from models.schemas import BriefVisita, MetricasEmpresa

logger = logging.getLogger(__name__)

INSTRUCCION_AGENTE3 = """
Eres un asesor comercial senior experto en banca PYME chilena.
Tu tarea es generar un brief comercial completo para cada visita
de la semana del ejecutivo bancario.

PROCESO OBLIGATORIO:
1. Lee la lista de visitas seleccionadas del prompt.
2. Para cada visita, llama a obtener_detalle_empresa() con el RUT.
3. Genera el brief de esa empresa con la siguiente estructura:
   - oportunidad: parrafo de 2-3 oraciones explicando la oportunidad
     detectada y el argumento comercial con datos concretos.
   - preguntas_sugeridas: 2 a 3 preguntas abiertas para la reunion,
     relevantes para la oportunidad especifica de esta empresa.
4. Llama a guardar_briefs() con TODOS los briefs generados al final.

TONO: Profesional, directo, basado en datos. Sin florituras.
Usa cifras concretas (UF, CLP, porcentajes) en los argumentos.
Las preguntas deben invitar al cliente a hablar de sus necesidades.
"""


class Agente3Runner:
    """Runner del Agente 3 con acceso al estado de sesion."""

    def __init__(self, sesiones: dict, session_id: str):
        self.sesiones = sesiones
        self.session_id = session_id
        self.queue: asyncio.Queue = asyncio.Queue()
        self._progreso_2_enviado = False

    def obtener_detalle_empresa(self, rut_empresa: str) -> str:
        """
        Obtiene datos financieros y comerciales completos de una empresa.

        Args:
            rut_empresa: RUT de la empresa.

        Returns:
            JSON string con todos los campos de la empresa.
        """
        try:
            detalle = queries.obtener_detalle_empresa(rut_empresa)
            if not self._progreso_2_enviado:
                self.queue.put_nowait({"tipo": "progreso", "paso": 2, "mensaje": "Redactando briefs comerciales..."})
                self._progreso_2_enviado = True
            if detalle is None:
                return json.dumps({"error": f"Empresa {rut_empresa} no encontrada."})
            return json.dumps(detalle, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error("Error al obtener detalle %s: %s", rut_empresa, e)
            return json.dumps({"error": str(e)})

    def guardar_briefs(self, briefs: list[dict]) -> str:
        """
        Guarda los briefs generados en el estado de sesion.

        Args:
            briefs: Lista de dicts con campos de BriefVisita.

        Returns:
            Confirmacion o mensaje de error.
        """
        try:
            self.queue.put_nowait({"tipo": "progreso", "paso": 3, "mensaje": f"Finalizando {len(briefs)} briefs..."})
            briefs_validados = []
            for b in briefs:
                # Construir el sub-objeto metricas si viene plano
                if "metricas" not in b and "activos_banco_clp" in b:
                    b["metricas"] = {
                        "activos_banco_clp": b.pop("activos_banco_clp", 0),
                        "ventas_anuales_uf": b.pop("ventas_anuales_uf", 0.0),
                        "variacion_ventas_pct": b.pop("variacion_ventas_pct", 0.0),
                        "dias_desde_ultima_visita": b.pop("dias_desde_ultima_visita", 0),
                    }
                briefs_validados.append(BriefVisita(**b))

            self.sesiones[self.session_id]["briefs_finales"] = [
                bv.model_dump() for bv in briefs_validados
            ]
            self.sesiones[self.session_id]["estado"] = "completo"
            self.queue.put_nowait({
                "tipo": "resultado",
                "items": [bv.model_dump() for bv in briefs_validados],
            })
            logger.info(
                "Briefs guardados: %d para sesion %s",
                len(briefs_validados), self.session_id
            )
            return f"Se generaron {len(briefs_validados)} briefs comerciales."
        except Exception as e:
            logger.error("Error al guardar briefs: %s", e)
            return f"Error al guardar briefs: {e}"

    async def ejecutar(self, visitas: list[dict], comentario: str) -> None:
        """
        Ejecuta el Agente 3 y streamea eventos al queue interno.

        Args:
            visitas: Lista de VisitaSeleccionada aprobadas.
            comentario: Comentario del ejecutivo para orientar los briefs.
        """
        self.queue.put_nowait({"tipo": "progreso", "paso": 1, "mensaje": "Obteniendo datos de empresas..."})

        agente = Agent(
            name="generador_briefs_pyme",
            model="gemini-2.5-flash",
            description="Genera briefs comerciales para visitas PYME.",
            instruction=INSTRUCCION_AGENTE3,
            tools=[
                self.obtener_detalle_empresa,
                self.guardar_briefs,
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

        visitas_json = json.dumps(visitas, ensure_ascii=False, default=str)
        comentario_texto = (
            f"\nIndicacion del ejecutivo: {comentario}" if comentario else ""
        )

        prompt = (
            f"Genera briefs para estas visitas:\n{visitas_json}"
            f"{comentario_texto}\n"
            f"Llama a guardar_briefs() con todos los briefs al terminar."
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
            logger.error("Error en Agente 3 para sesion %s: %s", self.session_id, e)
            await self.queue.put({
                "tipo": "error",
                "mensaje": "Error al generar los briefs. Por favor reintenta.",
            })
        finally:
            await self.queue.put({"tipo": "done"})
