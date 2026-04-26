/*
 * session.js — Gestion del estado global de la sesion.
 *
 * Responsabilidad: mantener el sessionId, datos del ejecutivo,
 * y proveer funciones de utilidad usadas por los otros modulos JS.
 *
 * Se carga primero en index.html para que las funciones esten
 * disponibles cuando los otros scripts se ejecuten.
 */

// Estado global de la sesion — un solo objeto, acceso directo
const sesion = {
  sessionId: null,
  nombreEjecutivo: null,
  sucursal: null,
  nEmpresasCartera: 0,
};

/**
 * Inicia la sesion llamando al backend y transiciona a la pantalla principal.
 *
 * @param {string} nombreEjecutivo - Nombre del ejecutivo seleccionado.
 */
async function iniciarSesion(nombreEjecutivo) {
  try {
    const resp = await fetch('/api/session/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nombre_ejecutivo: nombreEjecutivo }),
    });

    if (resp.status === 404) {
      mostrarToastError('El ejecutivo no fue encontrado en el sistema.');
      document.getElementById('btn-ingresar').disabled = false;
      document.getElementById('btn-ingresar').textContent = 'Ingresar al sistema';
      return;
    }
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }

    const datos = await resp.json();
    sesion.sessionId = datos.session_id;
    sesion.nombreEjecutivo = datos.nombre_ejecutivo;
    sesion.sucursal = datos.sucursal;
    sesion.nEmpresasCartera = datos.n_empresas_cartera;

    // Configurar topbar
    const iniciales = obtenerIniciales(datos.nombre_ejecutivo);
    document.getElementById('topbar-nombre').textContent = datos.nombre_ejecutivo;
    document.getElementById('topbar-detalle').textContent =
      `${datos.sucursal} · ${datos.n_empresas_cartera} empresas en cartera`;
    document.getElementById('topbar-avatar').textContent = iniciales;

    // Transicionar pantallas
    document.getElementById('pantalla-login').hidden = true;
    document.getElementById('pantalla-principal').hidden = false;

    // Iniciar Agente 1 automaticamente
    iniciarAgente(1);

  } catch (err) {
    console.error('Error al iniciar sesion:', err);
    mostrarToastError('Error al conectar con el sistema. Intenta nuevamente.');
    document.getElementById('btn-ingresar').disabled = false;
    document.getElementById('btn-ingresar').textContent = 'Ingresar al sistema';
  }
}

/**
 * Muestra el toast de error global por 5 segundos.
 *
 * @param {string} mensaje - Mensaje a mostrar al usuario.
 */
function mostrarToastError(mensaje) {
  const toast = document.getElementById('toast-error');
  toast.textContent = mensaje;
  toast.hidden = false;
  setTimeout(() => { toast.hidden = true; }, 5000);
}

/**
 * Extrae iniciales de un nombre completo (maximo 2 letras).
 *
 * @param {string} nombre - Nombre completo.
 * @returns {string} Iniciales en mayuscula.
 */
function obtenerIniciales(nombre) {
  return nombre.split(' ').filter(Boolean).slice(0, 2).map(p => p[0].toUpperCase()).join('');
}

/**
 * Actualiza el panel de resumen lateral con las visitas confirmadas.
 *
 * @param {Array} visitas - Lista de visitas seleccionadas o confirmadas.
 */
function actualizarResumen(visitas) {
  document.getElementById('stat-visitas').textContent = visitas.length || '—';
  if (visitas.length === 0) return;

  const scores = visitas.map(v => v.score_compuesto || 0);
  const promedio = scores.reduce((a, b) => a + b, 0) / scores.length;
  document.getElementById('stat-score').textContent = Math.round(promedio);

  const lista = document.getElementById('lista-confirmadas');
  lista.innerHTML = visitas.slice(0, 5).map(v => `
    <div class="resumen-mini-card">
      <div class="mini-card-nombre">${v.razon_social || v.razon_social}</div>
      <div class="mini-card-opp">${v.tipo_oportunidad || v.producto_recomendado || ''}</div>
    </div>
  `).join('');
}
