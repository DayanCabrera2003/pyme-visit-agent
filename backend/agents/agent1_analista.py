"""
Agente 1 — Analista de Cartera PYME.

Responsabilidad: analizar la cartera completa del ejecutivo y producir
un ranking priorizado con score compuesto y justificacion por empresa.

El agente usa Google ADK con Gemini 2.5 Flash. Las tools son metodos
de la clase Agente1Runner para que tengan acceso al estado de sesion
sin usar variables globales (patron mas seguro para concurrencia futura).
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from config import GEMINI_API_KEY
from db import queries
from models.schemas import EstadoSesion, RankingItem

logger = logging.getLogger(__name__)

# Instruccion de sistema del Agente 1.
# Detallada para que el LLM entienda exactamente que debe hacer y
# en que orden llamar las tools.
INSTRUCCION_AGENTE1 = """
Eres un analista financiero experto en el segmento PYME bancario chileno.
Tu tarea es analizar la cartera de clientes PYME de un ejecutivo bancario
y producir un ranking priorizado para la semana.

PROCESO OBLIGATORIO:
1. Llama a obtener_cartera() para cargar las empresas del ejecutivo.
2. Llama a obtener_mes_actual() para saber el mes actual.
3. Analiza CADA empresa considerando los 6 criterios de priorizacion.
4. Para cada empresa, escribe en tu razonamiento:
   - El score compuesto calculado
   - Por que recibe ese score
   - Que oportunidad principal tiene
5. Al terminar de analizar todas las empresas, llama a guardar_ranking()
   con el listado completo ordenado de mayor a menor score.

CRITERIOS DE PRIORIZACION (ya calculados en el score_oportunidad, pero debes
complementar con tu analisis cualitativo):
- Score de oportunidad de la BD (30%)
- Urgencia de visita: dias sin visitar (20%)
- Campana comercial vigente activa (15%)
- Estacionalidad favorable: peak en mes actual o siguiente (15%)
- Share of wallet bajo < 30%: potencial de crecimiento (10%)
- Riesgo de perdida: meses sin venta > 3 (10%)

FORMATO DE RAZONAMIENTO: Escribe en espanol claro y directo.
No uses bullets ni markdown. Escribe parrafos cortos mientras analizas.
Termina siempre llamando a guardar_ranking().
"""

# Meses en espanol para evaluar estacionalidad
MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


class Agente1Runner:
    """
    Runner del Agente 1 con acceso al estado de sesion.

    Los metodos de esta clase actuan como tools ADK.
    Se usa una clase en lugar de funciones sueltas para que las tools
    tengan acceso a sesiones y session_id sin variables globales.
    """

    def __init__(self, sesiones: dict, session_id: str):
        """
        Args:
            sesiones: Dict compartido con todas las sesiones activas.
            session_id: ID de la sesion actual.
        """
        self.sesiones = sesiones
        self.session_id = session_id
        self.queue: asyncio.Queue = asyncio.Queue()

    # --- Tools que el LLM puede llamar ---

    def obtener_cartera(self, nombre_ejecutivo: str) -> str:
        """
        Obtiene todas las empresas de la cartera del ejecutivo desde la BD.

        Args:
            nombre_ejecutivo: Nombre del ejecutivo tal como aparece en la BD.

        Returns:
            JSON string con lista de empresas y sus datos.
        """
        try:
            empresas = queries.obtener_cartera_ejecutivo(nombre_ejecutivo)
            logger.info(
                "Cartera cargada: %d empresas para '%s'",
                len(empresas), nombre_ejecutivo
            )
            return json.dumps(empresas, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error("Error al obtener cartera de '%s': %s", nombre_ejecutivo, e)
            return json.dumps({"error": str(e)})

    def obtener_mes_actual(self) -> str:
        """
        Retorna el nombre del mes actual en espanol.

        Returns:
            Nombre del mes (ej: "abril").
        """
        mes = datetime.now().month
        return MESES_ES[mes]

    def guardar_ranking(self, items: list[dict]) -> str:
        """
        Guarda el ranking producido por el agente en el estado de sesion.

        El LLM debe llamar esta funcion al terminar el analisis,
        con la lista de empresas ordenada de mayor a menor score.

        Args:
            items: Lista de dicts, cada uno con los campos de RankingItem.

        Returns:
            Confirmacion de guardado.
        """
        try:
            ranking_validado = [RankingItem(**item) for item in items]
            self.sesiones[self.session_id]["cartera_completa"] = [
                r.model_dump() for r in ranking_validado
            ]
            # Notificar al SSE que hay resultado disponible
            self.queue.put_nowait({
                "tipo": "resultado",
                "items": [r.model_dump() for r in ranking_validado],
            })
            logger.info(
                "Ranking guardado: %d empresas para sesion %s",
                len(ranking_validado), self.session_id
            )
            return f"Ranking guardado correctamente con {len(items)} empresas."
        except Exception as e:
            logger.error("Error al guardar ranking: %s", e)
            return f"Error al guardar ranking: {e}"

    # --- Logica de scoring (determinista, testeable sin LLM) ---

    def calcular_score(self, empresa: dict, mes_actual: str) -> float:
        """
        Calcula el score compuesto de una empresa segun los 6 criterios.

        No depende del LLM — es determinista y permite que el agente
        verifique sus calculos antes de escribir la justificacion.

        Args:
            empresa: Dict con campos de g4_visitas_pyme.
            mes_actual: Nombre del mes actual en espanol.

        Returns:
            Score entre 0 y 100.
        """
        score = 0.0

        # Criterio 1: score_oportunidad de la BD (30%)
        score += 0.30 * float(empresa.get("score_oportunidad", 0))

        # Criterio 2: urgencia de visita (20%) — normalizado a 90 dias maximos
        dias = float(empresa.get("dias_desde_ultima_visita", 0))
        score += 0.20 * min(dias / 90.0, 1.0) * 100

        # Criterio 3: campana vigente (+15 puntos fijos)
        if empresa.get("campana_vigente", False):
            score += 15.0

        # Criterio 4: estacionalidad — peak en mes actual o siguiente (+15)
        mes_peak = (empresa.get("mes_peak_negocio") or "").lower()
        mes_siguiente = self._mes_siguiente(mes_actual)
        if mes_peak in (mes_actual.lower(), mes_siguiente.lower()):
            score += 15.0

        # Criterio 5: SoW bajo < 30% — potencial de crecimiento (+10)
        sow = float(empresa.get("share_of_wallet_pct", 100))
        if sow < 30.0:
            score += 10.0

        # Criterio 6: riesgo de perdida — meses sin venta > 3 (+10)
        meses_sin_venta = int(empresa.get("meses_sin_venta", 0))
        if meses_sin_venta > 3:
            score += 10.0

        return min(round(score, 2), 100.0)

    def construir_tags(self, empresa: dict, mes_actual: str) -> list[str]:
        """
        Genera las etiquetas de contexto visibles para el ejecutivo.

        Args:
            empresa: Datos de la empresa.
            mes_actual: Mes actual para evaluar estacionalidad.

        Returns:
            Lista de strings con las etiquetas aplicables.
        """
        tags = []
        if empresa.get("campana_vigente"):
            tipo = empresa.get("tipo_campana_vigente") or "Comercial"
            tags.append(f"Campaña activa: {tipo}")

        mes_peak = (empresa.get("mes_peak_negocio") or "").lower()
        mes_siguiente = self._mes_siguiente(mes_actual)
        if mes_peak in (mes_actual.lower(), mes_siguiente.lower()):
            tags.append(f"Peak estacional: {mes_peak.capitalize()}")

        meses_sin = int(empresa.get("meses_sin_venta", 0))
        if meses_sin > 3:
            tags.append(f"Sin venta: {meses_sin} meses")

        sow = float(empresa.get("share_of_wallet_pct", 100))
        if sow < 30.0:
            tags.append(f"SoW bajo: {sow:.0f}%")

        return tags

    def _mes_siguiente(self, mes_actual: str) -> str:
        """Retorna el nombre del mes siguiente al dado."""
        meses = list(MESES_ES.values())
        idx = meses.index(mes_actual.lower()) if mes_actual.lower() in meses else 0
        return meses[(idx + 1) % 12]

    # --- Ejecucion del agente ---

    async def ejecutar(self, nombre_ejecutivo: str) -> None:
        """
        Ejecuta el Agente 1 y streamea eventos al queue interno.

        Los eventos son dicts con keys 'tipo' y datos especificos:
        - {"tipo": "token", "text": "..."} — fragmento de razonamiento
        - {"tipo": "resultado", "items": [...]} — ranking final
        - {"tipo": "error", "mensaje": "..."} — error durante ejecucion

        Args:
            nombre_ejecutivo: Nombre del ejecutivo a analizar.
        """
        agente = Agent(
            name="analista_cartera_pyme",
            model="gemini-2.5-flash",
            description="Analiza la cartera PYME de un ejecutivo bancario.",
            instruction=INSTRUCCION_AGENTE1,
            tools=[
                self.obtener_cartera,
                self.obtener_mes_actual,
                self.guardar_ranking,
            ],
        )

        runner = Runner(
            agent=agente,
            app_name="pyme_visit_agent",
            session_service=InMemorySessionService(),
        )

        prompt = (
            f"Analiza la cartera del ejecutivo '{nombre_ejecutivo}'. "
            f"Usa las tools en el orden indicado y termina llamando a guardar_ranking()."
        )

        try:
            async for event in runner.run_async(
                user_id=self.session_id,
                session_id=self.session_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part.from_text(prompt)],
                ),
            ):
                # Capturar tokens de razonamiento para streaming
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            await self.queue.put({"tipo": "token", "text": part.text})
        except Exception as e:
            logger.error("Error en Agente 1 para sesion %s: %s", self.session_id, e)
            await self.queue.put({
                "tipo": "error",
                "mensaje": "Error en el analisis de cartera. Por favor reintenta.",
            })
        finally:
            await self.queue.put({"tipo": "done"})
