/*
 * stream.js — Conexion SSE y renderizado de razonamiento en tiempo real.
 *
 * Responsabilidad: conectar al endpoint SSE de cada agente, renderizar
 * el razonamiento letra a letra, y disparar el renderizado de resultados
 * cuando llega el evento 'resultado'.
 *
 * Usa EventSource (nativo del navegador) para recibir los eventos SSE.
 * No usa WebSocket porque la comunicacion es unidireccional.
 */

// Referencia al EventSource activo (null si no hay stream en curso)
let eventoSource = null;

/**
 * Inicia el agente N conectando al SSE del backend.
 * Actualiza el UI del agente: abre la card, muestra badge "Analizando".
 *
 * @param {number} nAgente - Numero del agente (1, 2 o 3).
 */
function iniciarAgente(nAgente) {
  const card = document.getElementById(`card-agente-${nAgente}`);
  const cuerpo = document.getElementById(`cuerpo-agente-${nAgente}`);
  const badge = document.getElementById(`badge-${nAgente}`);
  const razonamiento = document.getElementById(`razonamiento-${nAgente}`);

  // Expandir card y marcar como activo
  card.dataset.estado = 'activo';
  cuerpo.hidden = false;
  razonamiento.textContent = '';
  razonamiento.classList.remove('completo');
  badge.textContent = '● Analizando';
  badge.className = 'agent-badge agent-badge--analizando';

  // Actualizar stepper
  actualizarStepper(nAgente, 'activo');

  // Conectar SSE
  const url = `/api/agent/${nAgente}/stream?session_id=${sesion.sessionId}`;
  eventoSource = new EventSource(url);

  eventoSource.addEventListener('token', e => {
    const data = JSON.parse(e.data);
    razonamiento.textContent += data.text;
    // Auto-scroll al final del razonamiento
    razonamiento.scrollTop = razonamiento.scrollHeight;
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
    razonamiento.classList.add('completo');
    badge.textContent = 'Listo';
    badge.className = 'agent-badge agent-badge--listo';

    // Si es el agente 3, mostrar output final directamente
    if (nAgente === 3) {
      mostrarOutputFinal();
    } else {
      // Mostrar seccion de aprobacion para agentes 1 y 2
      document.getElementById(`aprobacion-${nAgente}`).hidden = false;
    }
  });

  // Si la conexion SSE falla a nivel de red, mostrar boton de reintento
  eventoSource.onerror = () => {
    if (eventoSource.readyState === EventSource.CLOSED) {
      mostrarToastError('La conexión se interrumpió. Puedes reintentar el agente.');
      mostrarBotonReintentar(nAgente);
    }
  };
}

/**
 * Actualiza el estado visual del stepper.
 *
 * @param {number} nAgente - Numero del agente activo.
 * @param {string} estado - "activo" | "completado".
 */
function actualizarStepper(nAgente, estado) {
  const step = document.getElementById(`step-${nAgente}`);
  const sub = document.getElementById(`step-${nAgente}-sub`);
  step.dataset.estado = estado;
  sub.textContent = estado === 'activo' ? 'En análisis...' : 'Completado';

  if (estado === 'completado' && nAgente < 3) {
    const linea = document.getElementById(`linea-${nAgente}-${nAgente + 1}`);
    if (linea) linea.classList.add('completada');
  }
}

/**
 * Agrega un boton de "Reintentar" en la card del agente.
 *
 * @param {number} nAgente - Numero del agente.
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

  // Rellenar header del output
  const briefs = sesion.briefs || [];
  document.getElementById('output-subtitulo').textContent =
    `${sesion.nombreEjecutivo} · ${sesion.sucursal} · ${briefs.length} visitas priorizadas`;
  document.getElementById('out-n-visitas').textContent = briefs.length;
  const scores = briefs.map(b => b.score_compuesto || 0);
  document.getElementById('out-score').textContent =
    Math.round(scores.reduce((a,b) => a+b, 0) / (scores.length || 1));
  document.getElementById('out-campanas').textContent =
    briefs.filter(b => (b.tags || []).some(t => t.includes('Campaña'))).length;

  // Renderizar grid de briefs
  renderizarBriefs(briefs);
}
