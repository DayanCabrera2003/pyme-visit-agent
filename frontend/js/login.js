/*
 * login.js — Logica del buscador de ejecutivos y flujo de inicio de sesion.
 *
 * Responsabilidad: cargar ejecutivos de la BD, filtrar en tiempo real
 * y llamar a session.js para iniciar la sesion al seleccionar un ejecutivo.
 *
 * No hace fetch directamente al backend — usa la funcion iniciarSesion()
 * de session.js para mantener la logica de sesion centralizada.
 */

const inputBusqueda = document.getElementById('input-busqueda');
const listaEjecutivos = document.getElementById('lista-ejecutivos');
const loginError = document.getElementById('login-error');
const btnIngresar = document.getElementById('btn-ingresar');

// Ejecutivos cargados desde el backend al iniciar
let ejecutivos = [];

// Ejecutivo seleccionado actualmente
let ejecutivoSeleccionado = null;

/**
 * Carga la lista de ejecutivos desde el backend al cargar la pagina.
 * En caso de error, muestra mensaje y no bloquea el resto de la UI.
 */
async function cargarEjecutivos() {
  try {
    const resp = await fetch('/api/ejecutivos/');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    ejecutivos = await resp.json();
  } catch (err) {
    console.error('Error al cargar ejecutivos:', err);
    mostrarError('No se pudo cargar la lista de ejecutivos. Verifica la conexión.');
  }
}

/**
 * Filtra la lista de ejecutivos segun el texto ingresado.
 * Muestra hasta 8 resultados para no sobrecargar la lista.
 *
 * @param {string} texto - Texto de busqueda.
 */
function filtrarEjecutivos(texto) {
  const termino = texto.toLowerCase().trim();
  if (!termino) {
    listaEjecutivos.hidden = true;
    return;
  }

  const coincidencias = ejecutivos
    .filter(e => e.nombre_ejecutivo.toLowerCase().includes(termino))
    .slice(0, 8);

  if (coincidencias.length === 0) {
    loginError.hidden = false;
    listaEjecutivos.hidden = true;
    return;
  }

  loginError.hidden = true;
  renderizarLista(coincidencias);
}

/**
 * Renderiza los items de ejecutivo en la lista desplegable.
 *
 * @param {Array} items - Lista de ejecutivos a mostrar.
 */
function renderizarLista(items) {
  listaEjecutivos.innerHTML = items.map(e => {
    const iniciales = obtenerIniciales(e.nombre_ejecutivo);
    return `
      <div class="login-item" data-nombre="${e.nombre_ejecutivo}" data-sucursal="${e.sucursal}">
        <div class="ejecutivo-avatar">${iniciales}</div>
        <div>
          <div class="ejecutivo-nombre">${e.nombre_ejecutivo}</div>
          <div class="ejecutivo-sucursal">${e.sucursal}</div>
        </div>
      </div>
    `;
  }).join('');

  listaEjecutivos.hidden = false;
}

/**
 * Extrae las iniciales de un nombre completo (maximo 2 letras).
 *
 * @param {string} nombre - Nombre completo del ejecutivo.
 * @returns {string} Iniciales en mayuscula.
 */
function obtenerIniciales(nombre) {
  return nombre
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(p => p[0].toUpperCase())
    .join('');
}

function mostrarError(mensaje) {
  loginError.textContent = mensaje;
  loginError.hidden = false;
}

// Eventos de interaccion

inputBusqueda.addEventListener('input', e => {
  ejecutivoSeleccionado = null;
  btnIngresar.disabled = true;
  filtrarEjecutivos(e.target.value);
});

listaEjecutivos.addEventListener('click', e => {
  const item = e.target.closest('.login-item');
  if (!item) return;

  ejecutivoSeleccionado = {
    nombre: item.dataset.nombre,
    sucursal: item.dataset.sucursal,
  };

  inputBusqueda.value = item.dataset.nombre;
  listaEjecutivos.hidden = true;
  loginError.hidden = true;
  btnIngresar.disabled = false;
});

// Cerrar lista al hacer click fuera
document.addEventListener('click', e => {
  if (!e.target.closest('.login-campo')) {
    listaEjecutivos.hidden = true;
  }
});

btnIngresar.addEventListener('click', async () => {
  if (!ejecutivoSeleccionado) return;
  btnIngresar.disabled = true;
  btnIngresar.textContent = 'Iniciando sesión...';
  // iniciarSesion esta definida en session.js
  await iniciarSesion(ejecutivoSeleccionado.nombre);
});

// Cargar ejecutivos al arrancar la pagina
cargarEjecutivos();
