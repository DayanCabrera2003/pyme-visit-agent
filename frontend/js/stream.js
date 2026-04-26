/*
 * stream.js — Conexion SSE y actualizacion de progreso estructurado.
 *
 * Muestra el avance del agente como 3 pasos visuales (punto pulsante → verde),
 * no como texto crudo. Los tokens del LLM se ignoran en la UI.
 */

let eventoSource = null;

/**
 * Inicia el agente N: abre SSE, resetea pasos y activa el primer paso.
 *
 * @param {number} nAgente - Numero del agente (1, 2 o 3).
 */
function iniciarAgente(nAgente) {
  const card   = document.getElementById(`card-agente-${nAgente}`);
  const cuerpo = document.getElementById(`cuerpo-agente-${nAgente}`);
  const badge  = document.getElementById(`badge-${nAgente}`);

  card.dataset.estado = 'activo';
  cuerpo.hidden = false;
  badge.textContent = '● Analizando';
  badge.className = 'agent-badge agent-badge--analizando';

  // Resetear todos los pasos al estado pendiente
  for (let i = 1; i <= 3; i++) {
    const paso = document.getElementById(`p${nAgente}-${i}`);
    if (paso) paso.dataset.estado = 'pendiente';
  }
  // Activar primer paso de inmediato
  const p1 = document.getElementById(`p${nAgente}-1`);
  if (p1) p1.dataset.estado = 'activo';

  actualizarStepper(nAgente, 'activo');

  const url = `${API_BASE}/agent/${nAgente}/stream?session_id=${sesion.sessionId}`;
  eventoSource = new EventSource(url);

  // Tokens del LLM: pensamiento interno, no se muestra al usuario
  eventoSource.addEventListener('token', () => {});

  eventoSource.addEventListener('progreso', e => {
    const data = JSON.parse(e.data);
    actualizarProgreso(nAgente, data.paso, data.mensaje);
  });

  eventoSource.addEventListener('resultado', e => {
    const data = JSON.parse(e.data);
    renderizarResultados(nAgente, data.items);
  });

  eventoSource.addEventListener('error', e => {
    const data = JSON.parse(e.data);
    mostrarToastError(data.mensaje);
    eventoSource.close();
    badge.textContent = 'Error — reintenta';
    badge.className = 'agent-badge';
    mostrarBotonReintentar(nAgente);
  });

  eventoSource.addEventListener('done', () => {
    eventoSource.close();
    // Marcar todos los pasos como completados
    for (let i = 1; i <= 3; i++) {
      const paso = document.getElementById(`p${nAgente}-${i}`);
      if (paso) paso.dataset.estado = 'hecho';
    }
    badge.textContent = 'Listo';
    badge.className = 'agent-badge agent-badge--listo';

    if (nAgente === 3) {
      mostrarOutputFinal();
    } else {
      document.getElementById(`aprobacion-${nAgente}`).hidden = false;
    }
  });

  eventoSource.onerror = () => {
    if (eventoSource.readyState === EventSource.CLOSED) {
      mostrarToastError('La conexión se interrumpió. Puedes reintentar el agente.');
      mostrarBotonReintentar(nAgente);
    }
  };
}

/**
 * Actualiza el estado visual de los pasos de progreso.
 * Los pasos anteriores al actual quedan en "hecho", el actual en "activo".
 *
 * @param {number} nAgente - Numero del agente.
 * @param {number} paso    - Numero del paso activo (1, 2 o 3).
 * @param {string} mensaje - Texto a mostrar en el paso activo.
 */
function actualizarProgreso(nAgente, paso, mensaje) {
  for (let i = 1; i < paso; i++) {
    const el = document.getElementById(`p${nAgente}-${i}`);
    if (el) el.dataset.estado = 'hecho';
  }
  const el = document.getElementById(`p${nAgente}-${paso}`);
  if (el) {
    el.dataset.estado = 'activo';
    el.querySelector('.paso-texto').textContent = mensaje;
  }
}

/**
 * Actualiza el estado visual del stepper superior.
 *
 * @param {number} nAgente - Numero del agente.
 * @param {string} estado  - "activo" | "completado".
 */
function actualizarStepper(nAgente, estado) {
  const step = document.getElementById(`step-${nAgente}`);
  const sub  = document.getElementById(`step-${nAgente}-sub`);
  step.dataset.estado = estado;
  sub.textContent = estado === 'activo' ? 'En análisis...' : 'Completado';

  if (estado === 'completado' && nAgente < 3) {
    const linea = document.getElementById(`linea-${nAgente}-${nAgente + 1}`);
    if (linea) linea.classList.add('completada');
  }
}

/**
 * Muestra boton de reintento cuando el agente falla.
 *
 * @param {number} nAgente - Numero del agente fallido.
 */
function mostrarBotonReintentar(nAgente) {
  const aprobacion = document.getElementById(`aprobacion-${nAgente}`);
  aprobacion.hidden = false;
  const btn = document.getElementById(`btn-aprobar-${nAgente}`);
  btn.textContent = 'Reintentar agente';
  btn.onclick = () => iniciarAgente(nAgente);
}

/**
 * Muestra el output final con el grid de briefs.
 * Oculta el layout de agentes y muestra la seccion de briefs.
 */
function mostrarOutputFinal() {
  const layoutPrincipal = document.querySelector('.layout-principal');
  if (layoutPrincipal) layoutPrincipal.hidden = true;
  const outputFinal = document.getElementById('output-final');
  outputFinal.hidden = false;
  actualizarStepper(3, 'completado');

  const briefs = sesion.briefs || [];
  document.getElementById('output-subtitulo').textContent =
    `${sesion.nombreEjecutivo} · ${sesion.sucursal} · ${briefs.length} visitas priorizadas`;
  document.getElementById('out-n-visitas').textContent = briefs.length;
  const scores = briefs.map(b => b.score_compuesto || 0);
  document.getElementById('out-score').textContent =
    Math.round(scores.reduce((a, b) => a + b, 0) / (scores.length || 1));
  document.getElementById('out-campanas').textContent =
    briefs.filter(b => (b.tags || []).some(t => t.includes('Campaña'))).length;

  renderizarBriefs(briefs);
}
