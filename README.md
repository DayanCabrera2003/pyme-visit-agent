# Planificador de Visitas PYME

Sistema de agentes de inteligencia artificial que ayuda a ejecutivos bancarios a priorizar y planificar visitas semanales a clientes del segmento PYME. Desarrollado como proyecto universitario para el curso de IA en UDD (Grupo 4).

---

## Indice

1. [Descripcion del proyecto](#descripcion-del-proyecto)
2. [Arquitectura general](#arquitectura-general)
3. [Tecnologias utilizadas](#tecnologias-utilizadas)
4. [Estructura del repositorio](#estructura-del-repositorio)
5. [Como funciona el flujo completo](#como-funciona-el-flujo-completo)
6. [Los tres agentes](#los-tres-agentes)
7. [API REST](#api-rest)
8. [Base de datos](#base-de-datos)
9. [Requisitos previos](#requisitos-previos)
10. [Instalacion paso a paso](#instalacion-paso-a-paso)
11. [Configuracion de variables de entorno](#configuracion-de-variables-de-entorno)
12. [Levantar el proyecto](#levantar-el-proyecto)
13. [Ejecutar los tests](#ejecutar-los-tests)
14. [Uso de la interfaz web](#uso-de-la-interfaz-web)
15. [Notas de diseno importantes](#notas-de-diseno-importantes)

---

## Descripcion del proyecto

Un ejecutivo bancario del segmento PYME maneja una cartera de decenas o cientos de empresas. Decidir cuales visitar cada semana —y en que orden— es una tarea que combina datos financieros, historial de contacto, campanas vigentes y conocimiento del mercado. Este sistema automatiza esa prioridad con tres agentes de IA encadenados, cada uno con una responsabilidad especifica, y le permite al ejecutivo revisar y ajustar el resultado de cada etapa antes de continuar.

El flujo termina con un plan de visitas semanal descargable en PDF, con briefs individuales por empresa.

---

## Arquitectura general

```
+-------------------+        HTTP / SSE        +-------------------------+
|   Frontend        | <----------------------> |   Backend FastAPI       |
|   (HTML/CSS/JS)   |                          |   backend/main.py       |
+-------------------+                          +----------+--------------+
                                                          |
                              +--------------------------+--------------------------+
                              |                          |                         |
                    +---------+--------+   +-------------+------+   +-------------+------+
                    |  Agente 1        |   |  Agente 2          |   |  Agente 3          |
                    |  Analista        |   |  Estratega         |   |  Briefs            |
                    |  (ranking)       |   |  (seleccion)       |   |  (documentos)      |
                    +--------+---------+   +--------+-----------+   +--------+-----------+
                             |                      |                        |
                             +----------+-----------+------------------------+
                                        |
                              +---------+----------+
                              |  Google ADK        |
                              |  Gemini 2.5 Flash  |
                              +--------+-----------+
                                       |
                              +--------+-----------+
                              |  Supabase          |
                              |  PostgreSQL        |
                              |  (solo lectura)    |
                              +--------------------+
```

El backend es una API REST con FastAPI. Los agentes se ejecutan en el servidor y transmiten su progreso al frontend mediante SSE (Server-Sent Events). El estado de cada sesion vive en memoria mientras dura la sesion del ejecutivo.

---

## Tecnologias utilizadas

### Backend

| Componente        | Libreria               | Version  |
|-------------------|------------------------|----------|
| Framework web     | FastAPI                | 0.136.0  |
| Servidor ASGI     | uvicorn[standard]      | 0.46.0   |
| Agentes IA        | google-adk             | 1.31.1   |
| Modelo LLM        | Google Gemini 2.5 Flash| via genai|
| SDK Google Gemini | google-genai           | 1.73.1   |
| Base de datos     | psycopg2-binary        | 2.9.12   |
| Validacion datos  | pydantic               | 2.13.3   |
| Variables entorno | python-dotenv          | 1.2.2    |
| Generacion PDF    | weasyprint             | 68.1     |
| Tests             | pytest + pytest-asyncio| latest   |

### Frontend

- HTML5 semantico, CSS3 (flexbox + grid), JavaScript vanilla
- Sin frameworks de frontend (sin React, Vue ni Angular)
- Fuentes: Cormorant Garamond y JetBrains Mono via Google Fonts
- Comunicacion con backend: Fetch API y EventSource (SSE nativo del navegador)

### Infraestructura

- Base de datos: Supabase (PostgreSQL gestionado, acceso solo lectura)
- LLM: Google Gemini via Google AI Studio (capa gratuita disponible)
- Despliegue: compatible con Docker, sin requisitos de infraestructura especial

---

## Estructura del repositorio

```
pyme-visit-agent/
|
+-- backend/                         # Todo el codigo Python
|   |
|   +-- agents/                      # Un archivo por agente
|   |   +-- agent1_analista.py       # Agente 1: analiza cartera y genera ranking
|   |   +-- agent2_estratega.py      # Agente 2: selecciona visitas para la semana
|   |   +-- agent3_briefs.py         # Agente 3: genera briefs de cada visita
|   |   +-- __init__.py
|   |
|   +-- api/                         # Rutas HTTP, una responsabilidad por archivo
|   |   +-- ejecutivos.py            # GET /ejecutivos/
|   |   +-- session.py               # POST /session/start, GET /session/{id}
|   |   +-- agents.py                # SSE streams y endpoints de aprobacion
|   |   +-- export.py                # GET /plan/export (genera PDF)
|   |   +-- __init__.py
|   |
|   +-- db/                          # Capa de acceso a datos
|   |   +-- connection.py            # Pool de conexiones psycopg2 a Supabase
|   |   +-- queries.py               # Todas las consultas SQL del proyecto
|   |   +-- __init__.py
|   |
|   +-- models/                      # Esquemas de datos Pydantic
|   |   +-- schemas.py               # Todos los modelos de datos del proyecto
|   |   +-- __init__.py
|   |
|   +-- tests/                       # Suite de tests
|   |   +-- conftest.py              # Fixtures y configuracion de pytest
|   |   +-- test_agent1_tools.py     # Tests de herramientas del Agente 1
|   |   +-- test_agent2_tools.py     # Tests de herramientas del Agente 2
|   |   +-- test_agent3_tools.py     # Tests de herramientas del Agente 3
|   |   +-- test_api_agents.py       # Tests de endpoints de agentes
|   |   +-- test_api_ejecutivos.py   # Tests del endpoint de ejecutivos
|   |   +-- test_api_session.py      # Tests de gestion de sesion
|   |   +-- test_config.py           # Tests de carga de configuracion
|   |   +-- test_queries.py          # Tests de queries SQL
|   |   +-- test_schemas.py          # Tests de validacion de esquemas
|   |   +-- __init__.py
|   |
|   +-- config.py                    # Lee variables de entorno (unico punto)
|   +-- main.py                      # Inicializacion de FastAPI, CORS, lifespan
|   +-- sesiones_store.py            # Almacenamiento en memoria de sesiones activas
|   +-- requirements.txt             # Dependencias Python
|
+-- frontend/                        # Interfaz web
|   +-- index.html                   # Aplicacion de una sola pagina (SPA)
|   +-- js/
|   |   +-- config.js                # URL base del API
|   |   +-- login.js                 # Busqueda y seleccion de ejecutivo
|   |   +-- session.js               # Ciclo de vida de la sesion
|   |   +-- stream.js                # Conexion SSE y actualizacion de UI
|   |   +-- approval.js              # Flujo de aprobacion por agente
|   |   +-- export.js                # Descarga del PDF
|   +-- css/
|       +-- base.css                 # Layout y tipografia base
|       +-- login.css                # Pantalla de login
|       +-- stepper.css              # Barra de progreso (3 pasos)
|       +-- agent-card.css           # Tarjetas de cada agente
|       +-- briefs.css               # Vista de briefs finales
|
+-- .env.example                     # Plantilla de variables de entorno
+-- .gitignore                       # Archivos excluidos del repositorio
```

---

## Como funciona el flujo completo

El sistema divide el trabajo en tres etapas secuenciales. El ejecutivo puede revisar y ajustar el resultado de cada etapa antes de pasar a la siguiente.

### Paso 1 — Identificacion del ejecutivo

El ejecutivo entra a la interfaz web y busca su nombre en la lista. Al seleccionarse, el frontend llama a `POST /session/start` que crea una sesion en memoria y carga la cartera del ejecutivo desde la base de datos.

### Paso 2 — Agente 1: Analisis de cartera

El frontend abre una conexion SSE a `GET /agent/1/stream`. El Agente 1 analiza toda la cartera del ejecutivo y genera un ranking de empresas con puntajes del 0 al 100. El algoritmo de puntuacion es determinista y combina:

- **Score de oportunidad** de la base de datos: 30%
- **Dias sin visita** (normalizado a 90 dias): 20%
- **Campana activa** que coincide con la empresa: +15 puntos
- **Estacionalidad** (mes pico del rubro): +15 puntos
- **SoW bajo** (participacion de mercado menor al 30%): +10 puntos
- **Riesgo de fuga** (sin ventas hace mas de 3 meses): +10 puntos

Ademas detecta si algun rubro significativo de la cartera queda subrepresentado en el top 10 y genera advertencias al ejecutivo.

El ejecutivo revisa el ranking, puede descartar empresas y agregar un comentario, luego aprueba con `POST /agent/1/approve`.

### Paso 3 — Agente 2: Estrategia semanal

Con el ranking aprobado, el Agente 2 selecciona entre 5 y 7 empresas para visitar durante la semana. Aplica dos restricciones de negocio:

- Maximo 2 visitas por dia (lunes a viernes)
- Entre 5 y 7 visitas totales (objetivo semanal del banco)

Para cada visita selecciona el tipo de oportunidad, el producto a ofrecer y el argumento comercial. El ejecutivo revisa, puede descartar visitas y agrega comentarios, luego aprueba con `POST /agent/2/approve`.

### Paso 4 — Agente 3: Briefs de visita

El Agente 3 genera un brief completo para cada visita aprobada. Cada brief incluye la oportunidad identificada, metricas financieras relevantes de la empresa y preguntas sugeridas para la reunion. Los datos que el LLM no incluye en el brief son completados automaticamente desde la base de datos.

### Paso 5 — Exportacion

Con los briefs generados, el ejecutivo puede descargar el plan completo en PDF haciendo clic en el boton de exportacion. El endpoint `GET /plan/export` genera el PDF con WeasyPrint y lo entrega como descarga.

---

## Los tres agentes

Cada agente esta implementado como una clase `AgenteNRunner` en su propio archivo. El patron es consistente en los tres:

```python
class Agente1Runner:
    def __init__(self, sesiones: dict, session_id: str):
        # recibe el estado global de sesiones por referencia
        # define sus herramientas como metodos de la clase

    async def ejecutar(self, ...):
        # crea el Agent de Google ADK con system prompt + tools
        # ejecuta runner.run_async()
        # hace yield de eventos (progreso, resultado, error, done)
```

Las herramientas (tools) que cada agente puede llamar son funciones Python normales. El LLM decide cuando llamarlas y con que argumentos. El resultado de cada tool vuelve al LLM como contexto para continuar.

### Agente 1 — Herramientas disponibles

| Herramienta          | Descripcion                                              |
|----------------------|----------------------------------------------------------|
| `obtener_cartera()`  | Carga todas las empresas del ejecutivo desde la BD       |
| `obtener_mes_actual()` | Retorna el mes del sistema para calculo de estacionalidad |
| `guardar_ranking()`  | Persiste el ranking en la sesion activa                  |

### Agente 2 — Herramientas disponibles

| Herramienta                  | Descripcion                                        |
|------------------------------|----------------------------------------------------|
| `obtener_detalle_empresa()`  | Carga datos completos de una empresa por RUT       |
| `obtener_campanas_vigentes()` | Lista campanas activas del banco este mes          |
| `guardar_visitas()`          | Persiste la seleccion de visitas en la sesion      |

### Agente 3 — Herramientas disponibles

| Herramienta                  | Descripcion                                        |
|------------------------------|----------------------------------------------------|
| `obtener_detalle_empresa()`  | Carga datos completos de una empresa por RUT       |
| `guardar_briefs()`           | Persiste los briefs generados en la sesion         |

---

## API REST

### Ejecutivos

```
GET /ejecutivos/
```
Retorna la lista de todos los ejecutivos disponibles con su sucursal y regional.

Respuesta:
```json
[
  {
    "nombre_ejecutivo": "Maria Gonzalez",
    "sucursal": "Santiago Centro",
    "regional": "Metropolitana"
  }
]
```

---

### Sesion

```
POST /session/start
Body: { "nombre_ejecutivo": "Maria Gonzalez" }
```
Crea una sesion en memoria, verifica que el ejecutivo exista en la BD y carga su cartera. Retorna el `session_id` que el frontend guarda y envia en todas las llamadas siguientes.

Respuesta:
```json
{
  "session_id": "abc123",
  "nombre_ejecutivo": "Maria Gonzalez",
  "sucursal": "Santiago Centro",
  "n_empresas_cartera": 45
}
```

```
GET /session/{session_id}
```
Retorna el estado actual de la sesion (util para recuperar estado si se pierde la conexion).

---

### Agentes — Streaming (SSE)

```
GET /agent/1/stream?session_id={id}
GET /agent/2/stream?session_id={id}
GET /agent/3/stream?session_id={id}
```

Conexion SSE que transmite eventos mientras el agente trabaja. Los eventos tienen el formato `data: {...}\n\n` estandar de SSE.

Tipos de eventos:

| Evento      | Descripcion                                          |
|-------------|------------------------------------------------------|
| `progreso`  | Mensaje de texto sobre lo que esta haciendo el agente |
| `resultado` | JSON con el output estructurado del agente           |
| `error`     | Descripcion del error si algo falla                  |
| `done`      | El agente termino, se puede cerrar la conexion       |

---

### Agentes — Aprobacion

```
POST /agent/1/approve
Body: {
  "session_id": "abc123",
  "elementos_descartados": ["76123456-7", "88654321-0"],
  "comentario": "Prefiero omitir las empresas con deuda vencida"
}
```

```
POST /agent/2/approve
Body: {
  "session_id": "abc123",
  "elementos_descartados": ["76123456-7"],
  "comentario": "La visita del martes ya estaba agendada, mejor jueves"
}
```

Ambos endpoints filtran el resultado del agente correspondiente segun los elementos descartados y guardan el comentario para que el siguiente agente lo tenga como contexto.

---

### Exportacion

```
GET /plan/export?session_id={id}
```
Genera y descarga el plan de visitas semanal en PDF. Requiere que el Agente 3 haya completado su ejecucion.

---

### Health check

```
GET /health
Respuesta: { "status": "ok" }
```

---

## Base de datos

El proyecto usa una tabla en Supabase PostgreSQL llamada `g4_visitas_pyme`. El acceso es **solo lectura** — el sistema nunca escribe en la base de datos.

### Campos principales de la tabla

| Campo                    | Tipo    | Descripcion                                      |
|--------------------------|---------|--------------------------------------------------|
| `rut_empresa`            | text    | RUT de la empresa (identificador unico)          |
| `razon_social`           | text    | Nombre legal de la empresa                       |
| `nombre_ejecutivo`       | text    | Ejecutivo responsable de la cuenta               |
| `sucursal`               | text    | Sucursal bancaria del ejecutivo                  |
| `regional`               | text    | Regional del banco                               |
| `score_oportunidad`      | integer | Puntaje de oportunidad comercial (0-100)         |
| `fecha_ultima_visita`    | date    | Fecha de la ultima visita registrada             |
| `campana_activa`         | boolean | Si hay una campana bancaria activa para la empresa|
| `mes_peak`               | integer | Mes de mayor actividad del rubro (1-12)          |
| `sow`                    | numeric | Share of Wallet (participacion de mercado, 0-1)  |
| `meses_sin_venta`        | integer | Meses consecutivos sin operaciones               |
| `activos`                | numeric | Total de activos de la empresa                   |
| `ventas`                 | numeric | Ventas anuales                                   |
| `rubro`                  | text    | Sector economico de la empresa                   |
| `direccion`              | text    | Direccion de la empresa                          |

### Consultas SQL usadas

El archivo `backend/db/queries.py` contiene todas las consultas del proyecto:

- `obtener_ejecutivos()` — lista de ejecutivos unicos con sucursal y regional
- `obtener_cartera_ejecutivo(nombre)` — todas las empresas de un ejecutivo
- `obtener_detalle_empresa(rut)` — datos completos de una empresa por RUT

Todas las consultas usan parametros para prevenir inyeccion SQL.

---

## Requisitos previos

Antes de instalar el proyecto necesitas tener:

- **Python 3.10 o superior** — el proyecto usa sintaxis de type hints y async/await moderno
- **pip** — gestor de paquetes de Python (incluido con Python)
- **Git** — para clonar el repositorio
- **Google Gemini API Key** — gratuita, se obtiene en [aistudio.google.com](https://aistudio.google.com/app/apikey)
- **Credenciales de Supabase** — la cadena de conexion `DATABASE_URL` al proyecto de Supabase con la tabla `g4_visitas_pyme`

Para servir el frontend necesitas una de estas opciones:
- Extension **Live Server** en VS Code (recomendado para desarrollo)
- Python (incluido, ya lo tienes)
- Node.js con `http-server` (opcional)

### Verificar Python

```bash
python --version
# Debe mostrar Python 3.10.x o superior
```

### WeasyPrint — dependencias del sistema

WeasyPrint (generacion de PDF) requiere bibliotecas del sistema. Instalalas segun tu sistema operativo:

**Ubuntu / Debian / Fedora:**
```bash
# Ubuntu / Debian
sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi-dev

# Fedora
sudo dnf install pango harfbuzz libffi-devel
```

**macOS:**
```bash
brew install pango
```

**Windows:**
Instalar GTK3 desde [github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer)

---

## Instalacion paso a paso

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd pyme-visit-agent
```

### 2. Crear entorno virtual

```bash
# Linux / macOS
python -m venv venv
source venv/bin/activate

# Windows (cmd)
python -m venv venv
venv\Scripts\activate

# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

El prompt del terminal deberia mostrar `(venv)` al inicio.

### 3. Instalar dependencias

```bash
pip install -r backend/requirements.txt
```

La instalacion puede tardar varios minutos la primera vez porque WeasyPrint tiene muchas dependencias.

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Abre el archivo `.env` con cualquier editor y reemplaza los valores de ejemplo con los reales:

```
GEMINI_API_KEY=AIzaSyD...          <- tu API key de Google AI Studio
DATABASE_URL=postgresql://...      <- cadena de conexion de Supabase
PORT=8000
SESSION_TTL_MINUTES=60
```

Ver la seccion [Configuracion de variables de entorno](#configuracion-de-variables-de-entorno) para mas detalles.

---

## Configuracion de variables de entorno

El archivo `.env` en la raiz del proyecto debe contener:

### Variables obligatorias

| Variable        | Descripcion                          | Donde obtenerla                              |
|-----------------|--------------------------------------|----------------------------------------------|
| `GEMINI_API_KEY` | API Key de Google Gemini             | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| `DATABASE_URL`  | Cadena de conexion PostgreSQL        | Panel de Supabase > Settings > Database      |

La cadena `DATABASE_URL` tiene el formato:
```
postgresql://usuario:password@host:5432/postgres
```

En Supabase la encontras en: **Project Settings > Database > Connection string > URI**. Asegurate de copiar la version **Transaction pooler** (puerto 6543) si usas muchas conexiones concurrentes, o la **Direct connection** (puerto 5432) para desarrollo.

### Variables opcionales

| Variable              | Valor por defecto | Descripcion                              |
|-----------------------|-------------------|------------------------------------------|
| `PORT`                | 8000              | Puerto donde escucha el servidor FastAPI |
| `SESSION_TTL_MINUTES` | 60                | Minutos antes de que expire una sesion   |

### Verificar la configuracion

El backend valida las variables al arrancar. Si falta `GEMINI_API_KEY` o `DATABASE_URL`, el servidor lanza un `ValueError` con un mensaje claro antes de iniciar.

---

## Levantar el proyecto

El proyecto tiene dos partes independientes: backend y frontend. Ambas deben estar corriendo al mismo tiempo.

### Levantar el backend

Con el entorno virtual activado:

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

El flag `--reload` reinicia el servidor automaticamente cuando modificas un archivo Python (util para desarrollo).

Si el arranque es exitoso, veras en la consola:
```
INFO:     Pool de BD inicializado.
INFO:     Tarea de limpieza de sesiones iniciada.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Verifica que funciona:
```bash
curl http://localhost:8000/health
# Debe retornar: {"status":"ok"}
```

La documentacion interactiva de la API esta disponible en:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Levantar el frontend

El frontend es HTML/CSS/JS estatico y debe servirse desde un servidor HTTP (no abrir directamente como `file://` porque el navegador bloquea las peticiones fetch desde origenes locales).

**Opcion A — Extension Live Server (VS Code, recomendada):**
1. Instalar la extension "Live Server" de Ritwick Dey en VS Code
2. Abrir la carpeta `frontend/` en VS Code
3. Clic derecho en `index.html` > "Open with Live Server"
4. El navegador abre automaticamente en `http://127.0.0.1:5500`

**Opcion B — Python (sin instalacion adicional):**
```bash
cd frontend
python -m http.server 5500
# Abrir http://localhost:5500 en el navegador
```

**Opcion C — Node.js:**
```bash
npx http-server frontend -p 5500
# Abrir http://localhost:5500
```

### Verificar que todo funciona

1. El backend corre en `http://localhost:8000`
2. El frontend corre en `http://localhost:5500` (o `http://127.0.0.1:5500`)
3. En el navegador, la pantalla de login debe mostrar un campo de busqueda
4. Al escribir en el campo, debe aparecer la lista de ejecutivos cargada desde el backend
5. Si la lista no aparece, revisar la consola del navegador (F12) y los logs del backend

---

## Ejecutar los tests

Desde la raiz del proyecto con el entorno virtual activado:

```bash
cd backend
pytest tests/ -v
```

Para ejecutar un archivo de tests especifico:
```bash
pytest tests/test_agent1_tools.py -v
```

Para ver el reporte de cobertura:
```bash
pytest tests/ -v --tb=short
```

### Sobre los tests

Los tests mockean las llamadas externas (Gemini API y base de datos) para que puedan correr sin credenciales reales ni conexion a internet. El archivo `tests/conftest.py` define los fixtures compartidos.

Los tests cubren:
- Herramientas de cada agente (logica de scoring, validaciones)
- Endpoints de la API (status codes, contratos de datos)
- Carga de configuracion (variables de entorno)
- Consultas SQL (estructura de resultados)
- Validacion de esquemas Pydantic

---

## Uso de la interfaz web

### Pantalla de login

Al abrir el frontend aparece una pantalla con un campo de busqueda. Escribe el nombre del ejecutivo (o parte de el) para filtrar la lista. Haz clic en el nombre para seleccionarlo y comenzar la sesion.

### Paso 1 — Ranking de cartera

Despues de iniciar sesion, el sistema ejecuta automaticamente el Agente 1. Una barra de progreso indica que el agente esta trabajando. Cuando termina, aparece una tabla con todas las empresas de la cartera ordenadas por puntaje de prioridad, con la justificacion y etiquetas contextuales para cada una.

Puedes desmarcar empresas que no quieras incluir en el analisis del siguiente paso. Opcionalmente puedes agregar un comentario para el agente. Cuando estes conforme, haz clic en **Aprobar y continuar**.

### Paso 2 — Seleccion de visitas

El Agente 2 selecciona las visitas optimas de la semana basandose en el ranking aprobado. Muestra un calendario con las visitas distribuidas de lunes a viernes, con el tipo de oportunidad y producto recomendado para cada una.

Puedes descartar visitas individuales y agregar comentarios antes de aprobar.

### Paso 3 — Briefs de visita

El Agente 3 genera un brief completo para cada visita aprobada. Cada brief muestra la oportunidad identificada, metricas financieras clave de la empresa y preguntas sugeridas para guiar la reunion.

### Exportacion

Una vez completados los tres pasos, aparece el boton **Descargar plan PDF** en el panel lateral. Haz clic para descargar el plan semanal completo en formato PDF.

---

## Notas de diseno importantes

### Por que tres agentes separados y no uno solo

Dividir el trabajo en tres agentes con responsabilidades distintas tiene ventajas concretas:

- **Revision incremental:** El ejecutivo puede corregir el rumbo entre cada etapa. Si el ranking del Agente 1 tiene un error, se corrige antes de que afecte los siguientes pasos.
- **Prompts mas pequenos:** Cada agente tiene un system prompt enfocado en una sola tarea, lo que reduce errores del LLM.
- **Testabilidad:** Cada agente puede testearse por separado con inputs controlados.

### Por que el scoring del Agente 1 es deterministico

El algoritmo de puntuacion del Agente 1 esta implementado en Python puro, no delegado al LLM. Esto garantiza que el mismo input siempre produce el mismo ranking, lo que hace el sistema auditoriable y los tests reproducibles. El LLM solo genera las justificaciones en lenguaje natural.

### Por que el estado de sesion vive en memoria

Dado que es un proyecto educativo con sesiones cortas (tipicamente menos de 30 minutos por uso), un store en memoria es suficiente y elimina la complejidad de una base de datos adicional para el estado. Una sesion expira a los 60 minutos de inactividad. En produccion se reemplazaria por Redis u otro store externo.

### Por que SSE en lugar de WebSockets

Los Server-Sent Events son unidireccionales (servidor -> cliente), lo que es exactamente lo que se necesita para transmitir el progreso de los agentes. Son mas simples que WebSockets, nativos del navegador y funcionan bien con proxies HTTP estandar.

---

## Problemas frecuentes

**El backend no arranca y dice `ValueError: Falta variable de entorno`**
El archivo `.env` no existe o le falta la variable indicada. Revisa que copiaste `.env.example` a `.env` y completaste todos los valores.

**El frontend no muestra la lista de ejecutivos**
Verifica que el backend este corriendo en el puerto 8000. Abre la consola del navegador (F12 > Console) para ver el error especifico. Tambien verifica que el archivo `frontend/js/config.js` tenga la URL correcta del backend.

**Error `CORS` en la consola del navegador**
El frontend debe servirse desde `localhost:5500` o `127.0.0.1:5500`. Si usas otro puerto, agrega el origen al array `allow_origins` en `backend/main.py`.

**La exportacion PDF falla**
WeasyPrint requiere bibliotecas del sistema (Pango, HarfBuzz). Revisa la seccion [WeasyPrint — dependencias del sistema](#weasyprint--dependencias-del-sistema) para instalar las dependencias segun tu sistema operativo.

**El agente falla con error 503 de Gemini**
La API de Gemini tiene limites de tasa en la capa gratuita. El Agente 3 tiene retry con backoff exponencial incorporado. Si el error persiste, espera unos minutos e intenta de nuevo.
