/*
 * export.js — Renderizado del grid de briefs y descarga del PDF.
 *
 * Responsabilidad: renderizar las tarjetas de brief en el grid
 * y manejar el click del boton de exportacion PDF.
 */

/**
 * Renderiza el grid de briefs en el output final.
 *
 * @param {Array} briefs - Lista de BriefVisita del Agente 3.
 */
function renderizarBriefs(briefs) {
  // Guardar en sesion para el SSE y el export
  sesion.briefs = briefs;
  const grid = document.getElementById('grid-briefs');

  grid.innerHTML = briefs.map((brief, idx) => {
    const m = brief.metricas || {};
    const activosF = m.activos_banco_clp
      ? `$${(m.activos_banco_clp / 1e6).toFixed(0)}M`
      : '—';
    const ventasF = m.ventas_anuales_uf
      ? `${m.ventas_anuales_uf.toFixed(0)} UF`
      : '—';
    const varF = m.variacion_ventas_pct !== undefined
      ? `${m.variacion_ventas_pct > 0 ? '+' : ''}${m.variacion_ventas_pct.toFixed(1)}%`
      : '—';

    const tagsHtml = (brief.tags || []).map(t => {
      const clase = t.includes('Campaña') ? 'tag--campana'
                  : t.includes('Peak')    ? 'tag--seasonal'
                  : t.includes('Sin venta') || t.includes('meses') ? 'tag--riesgo'
                  : t.includes('SoW')     ? 'tag--sow'
                  : '';
      return `<span class="tag ${clase}">${t}</span>`;
    }).join('');

    const preguntasHtml = (brief.preguntas_sugeridas || [])
      .map(p => `<li>${p}</li>`)
      .join('');

    const diaLabel = brief.dia_visita || `Visita ${idx + 1}`;

    return `
      <div class="brief-card" data-prioridad="${idx + 1}">
        <div class="brief-top">
          <div>
            <div class="brief-rank">Visita #${idx + 1} — ${diaLabel}</div>
            <div class="brief-empresa">${brief.razon_social}</div>
            <div class="brief-rubro">${brief.rubro} · ${brief.direccion}</div>
          </div>
          <div class="score-circulo">
            <div class="score-circulo-n">${Math.round(brief.score_compuesto || 0)}</div>
            <div class="score-circulo-l">Score</div>
          </div>
        </div>
        <div class="brief-tags-fila">${tagsHtml}</div>
        <div class="brief-metricas">
          <div><div class="metrica-val">${activosF}</div><div class="metrica-lbl">Activos banco</div></div>
          <div><div class="metrica-val">${ventasF}</div><div class="metrica-lbl">Ventas anuales</div></div>
          <div><div class="metrica-val">${varF}</div><div class="metrica-lbl">Var. ventas</div></div>
        </div>
        <div class="brief-seccion">
          <div class="seccion-label">Oportunidad identificada</div>
          <div class="brief-texto">${brief.oportunidad}</div>
        </div>
        <div class="brief-seccion">
          <div class="seccion-label">Preguntas sugeridas</div>
          <ul class="brief-preguntas">${preguntasHtml}</ul>
        </div>
      </div>
    `;
  }).join('');
}

// Boton de exportacion PDF
document.getElementById('btn-exportar-pdf').addEventListener('click', async () => {
  const btn = document.getElementById('btn-exportar-pdf');
  btn.disabled = true;
  btn.textContent = 'Generando PDF...';

  try {
    const resp = await fetch(`${API_BASE}/plan/export?session_id=${sesion.sessionId}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    // Descargar el blob del PDF
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `plan_visitas_pyme_${sesion.nombreEjecutivo.replace(/ /g, '_')}.pdf`;
    a.click();
    URL.revokeObjectURL(url);

  } catch (err) {
    console.error('Error al exportar PDF:', err);
    mostrarToastError('Error al generar el PDF. Intenta nuevamente.');
  } finally {
    btn.disabled = false;
    btn.textContent = '⬇ Exportar como PDF';
  }
});
