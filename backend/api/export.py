"""
Router para exportacion del plan semanal como PDF.

Usa WeasyPrint para convertir una plantilla HTML a PDF.
El PDF es A4 con estilos minimalistas en blanco para impresion.
"""
import logging
from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from sesiones_store import SESIONES

logger = logging.getLogger(__name__)
router = APIRouter()

# Plantilla HTML del PDF — separada de la logica para facilitar cambios visuales.
# Usa estilos inline para garantizar compatibilidad con WeasyPrint.
PLANTILLA_PDF = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; font-size: 12px; color: #1a1a1a; margin: 0; padding: 20px; }}
  h1 {{ font-size: 18px; font-weight: bold; border-bottom: 2px solid #1a1a1a; padding-bottom: 8px; }}
  h2 {{ font-size: 14px; font-weight: bold; margin-top: 24px; }}
  .ejecutivo {{ color: #555; font-size: 11px; margin-bottom: 16px; }}
  .brief {{ border: 1px solid #ddd; border-radius: 4px; padding: 14px; margin-bottom: 16px; page-break-inside: avoid; }}
  .brief-header {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
  .empresa {{ font-weight: bold; font-size: 13px; }}
  .dia {{ color: #555; font-size: 11px; }}
  .tags {{ margin: 6px 0; }}
  .tag {{ background: #f0f0f0; border: 1px solid #ddd; border-radius: 10px; padding: 2px 8px; font-size: 10px; margin-right: 4px; }}
  .metricas {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin: 8px 0; background: #f8f8f8; padding: 8px; border-radius: 4px; }}
  .metrica-valor {{ font-weight: bold; font-size: 13px; }}
  .metrica-label {{ font-size: 10px; color: #777; }}
  .seccion-label {{ font-size: 10px; color: #777; text-transform: uppercase; letter-spacing: 1px; margin: 10px 0 4px; }}
  .oportunidad {{ line-height: 1.5; }}
  .preguntas {{ padding-left: 16px; }}
  .preguntas li {{ margin-bottom: 4px; }}
  .footer {{ margin-top: 24px; border-top: 1px solid #ddd; padding-top: 8px; color: #aaa; font-size: 10px; }}
</style>
</head>
<body>
<h1>Plan de Visitas PYME -- Semana {semana}</h1>
<div class="ejecutivo">
  Ejecutivo: <strong>{nombre_ejecutivo}</strong> &nbsp;|&nbsp;
  Sucursal: {sucursal} &nbsp;|&nbsp;
  Visitas planificadas: {n_visitas}
</div>
{briefs_html}
<div class="footer">Generado por el Sistema de Planificacion de Visitas PYME -- Confidencial</div>
</body>
</html>
"""

BRIEF_TEMPLATE = """
<div class="brief">
  <div class="brief-header">
    <div>
      <div class="empresa">{razon_social}</div>
      <div class="ejecutivo">{rubro} &nbsp;|&nbsp; {direccion}</div>
    </div>
    <div class="dia">Visita: <strong>{dia_visita}</strong> &nbsp;|&nbsp; Score: <strong>{score}</strong></div>
  </div>
  <div class="tags">
    {tags_html}
  </div>
  <div class="metricas">
    <div>
      <div class="metrica-valor">${activos_banco:,.0f}</div>
      <div class="metrica-label">Activos en banco</div>
    </div>
    <div>
      <div class="metrica-valor">{ventas_anuales:,.0f} UF</div>
      <div class="metrica-label">Ventas anuales</div>
    </div>
    <div>
      <div class="metrica-valor">{variacion_ventas:+.1f}%</div>
      <div class="metrica-label">Variacion ventas</div>
    </div>
  </div>
  <div class="seccion-label">Oportunidad detectada</div>
  <div class="oportunidad">{oportunidad}</div>
  <div class="seccion-label">Preguntas sugeridas para la visita</div>
  <ul class="preguntas">{preguntas_html}</ul>
</div>
"""


def _construir_html(sesion: dict) -> str:
    """
    Construye el HTML completo del plan para convertir a PDF.

    Args:
        sesion: Dict con el estado completo de la sesion.

    Returns:
        String HTML listo para WeasyPrint.
    """
    from datetime import date
    briefs = sesion.get("briefs_finales", [])
    semana = date.today().strftime("%d de %B de %Y")

    briefs_html = ""
    for b in briefs:
        metricas = b.get("metricas", {})
        tags_html = " ".join(
            f'<span class="tag">{tag}</span>' for tag in b.get("tags", [])
        )
        preguntas_html = "".join(
            f"<li>{p}</li>" for p in b.get("preguntas_sugeridas", [])
        )
        briefs_html += BRIEF_TEMPLATE.format(
            razon_social=b.get("razon_social", ""),
            rubro=b.get("rubro", ""),
            direccion=b.get("direccion", ""),
            dia_visita=b.get("dia_visita", ""),
            score=b.get("score_compuesto", 0),
            tags_html=tags_html,
            activos_banco=metricas.get("activos_banco_clp", 0),
            ventas_anuales=metricas.get("ventas_anuales_uf", 0),
            variacion_ventas=metricas.get("variacion_ventas_pct", 0),
            oportunidad=b.get("oportunidad", ""),
            preguntas_html=preguntas_html,
        )

    return PLANTILLA_PDF.format(
        semana=semana,
        nombre_ejecutivo=sesion.get("nombre_ejecutivo", ""),
        sucursal=sesion.get("sucursal", ""),
        n_visitas=len(briefs),
        briefs_html=briefs_html,
    )


@router.get("/export")
async def exportar_plan(session_id: str):
    """
    Genera el plan semanal como PDF y lo retorna para descarga.

    Requiere que el Agente 3 haya completado (briefs_finales no vacio).
    """
    sesion = SESIONES.get(session_id)
    if sesion is None:
        raise HTTPException(status_code=410, detail="Sesion no encontrada o expirada.")

    briefs = sesion.get("briefs_finales", [])
    if not briefs:
        raise HTTPException(
            status_code=400,
            detail="El plan aun no esta completo. Finaliza los 3 agentes antes de exportar.",
        )

    try:
        # WeasyPrint puede ser lento en el primer uso (carga fuentes del sistema)
        from weasyprint import HTML
        html_content = _construir_html(sesion)
        pdf_bytes = HTML(string=html_content).write_pdf()

        nombre_ejecutivo = sesion.get("nombre_ejecutivo", "ejecutivo").replace(" ", "_")
        filename = f"plan_visitas_pyme_{nombre_ejecutivo}.pdf"

        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error("Error al generar PDF para sesion %s: %s", session_id, e)
        raise HTTPException(
            status_code=500,
            detail="Error al generar el PDF. Por favor intenta nuevamente.",
        )
