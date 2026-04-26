/*
 * approval.js — Logica de aprobacion, checkboxes y envio al backend.
 *
 * Responsabilidad: renderizar la tabla de empresas/visitas con checkboxes,
 * manejar la seleccion/deseleccion, y enviar la aprobacion al backend.
 */

/**
 * Renderiza la lista de items (empresas o visitas) con checkboxes.
 * Se llama cuando llega el evento 'resultado' del SSE.
 *
 * @param {number} nAgente - Numero del agente (1 o 2).
 * @param {Array} items - Lista de RankingItem o VisitaSeleccionada.
 */
function renderizarResultados(nAgente, items) {
  const contenedor = document.getElementById(`tabla-empresas-${nAgente}`);
  const seccion = document.getElementById(`resultados-${nAgente}`);

  // Guardar items en el estado de sesion para el envio posterior
  if (nAgente === 1) sesion.carteraCompleta = items;
  if (nAgente === 2) sesion.visitasSeleccionadas = items;

  contenedor.innerHTML = items.map((item, idx) => {
    const nombre = item.razon_social;
    const rut = item.rut_empresa;
    const score = item.score_compuesto || 0;
    const tags = item.tags || [];
    const tagsHtml = tags.map(t => {
      const clase = t.includes('Campaña') ? 'tag--campana'
                  : t.includes('Peak')    ? 'tag--seasonal'
                  : t.includes('Sin venta') || t.includes('meses') ? 'tag--riesgo'
                  : t.includes('SoW')     ? 'tag--sow'
                  : '';
      return `<span class="tag ${clase}">${t}</span>`;
    }).join('');

    const pct = Math.round(score);

    return `
      <div class="empresa-fila" id="fila-${nAgente}-${rut}">
        <span class="empresa-rank">${idx + 1}</span>
        <div class="empresa-check marcado" data-rut="${rut}" data-agente="${nAgente}"
             onclick="toggleEmpresa(this)">✓</div>
        <span class="empresa-nombre">${nombre}</span>
        ${item.rubro ? `<span class="empresa-rubro">${item.rubro}</span>` : ''}
        <div class="empresa-tags">${tagsHtml}</div>
        <div class="score-wrap">
          <div class="score-bar"><div class="score-fill" style="width:${pct}%"></div></div>
          <div class="score-num">${pct}</div>
        </div>
      </div>
    `;
  }).join('');

  seccion.hidden = false;
  actualizarResumen(items);
}

/**
 * Alterna el estado de aprobacion de una empresa al hacer click en el checkbox.
 *
 * @param {HTMLElement} check - El div del checkbox que recibio el click.
 */
function toggleEmpresa(check) {
  const estaAprobado = check.classList.contains('marcado');
  const rut = check.dataset.rut;
  const nAgente = check.dataset.agente;
  const fila = document.getElementById(`fila-${nAgente}-${rut}`);

  if (estaAprobado) {
    check.classList.remove('marcado');
    check.textContent = '';
    fila.classList.add('descartada');
  } else {
    check.classList.add('marcado');
    check.textContent = '✓';
    fila.classList.remove('descartada');
  }
}

/**
 * Recolecta los RUTs descartados y envia la aprobacion al backend.
 *
 * @param {number} nAgente - Agente cuya aprobacion se esta enviando.
 */
async function enviarAprobacion(nAgente) {
  const checks = document.querySelectorAll(
    `.empresa-check[data-agente="${nAgente}"]:not(.marcado)`
  );
  const descartados = Array.from(checks).map(c => c.dataset.rut);
  const comentario = (document.getElementById(`comentario-${nAgente}`) || {}).value || '';

  const btn = document.getElementById(`btn-aprobar-${nAgente}`);
  btn.disabled = true;
  btn.textContent = 'Procesando...';

  try {
    const resp = await fetch(`${API_BASE}/agent/${nAgente}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sesion.sessionId,
        elementos_descartados: descartados,
        comentario: comentario,
      }),
    });

    if (resp.status === 410) {
      mostrarToastError('La sesión expiró. Recarga la página e ingresa nuevamente.');
      return;
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    // Colapsar card actual y marcar como completada
    const cardActual = document.getElementById(`card-agente-${nAgente}`);
    cardActual.dataset.estado = 'completado';
    document.getElementById(`badge-${nAgente}`).textContent = 'Aprobado ✓';
    document.getElementById(`badge-${nAgente}`).className = 'agent-badge agent-badge--listo';
    actualizarStepper(nAgente, 'completado');

    // Iniciar siguiente agente
    if (nAgente < 3) {
      iniciarAgente(nAgente + 1);
    }

  } catch (err) {
    console.error('Error al enviar aprobacion:', err);
    mostrarToastError('Error al procesar la aprobación. Intenta nuevamente.');
    btn.disabled = false;
    btn.textContent = `Continuar al Agente ${nAgente + 1} →`;
  }
}

// Conectar botones de aprobacion
document.getElementById('btn-aprobar-1').addEventListener('click', () => enviarAprobacion(1));
document.getElementById('btn-aprobar-2').addEventListener('click', () => enviarAprobacion(2));
