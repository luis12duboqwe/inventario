# Arquitectura LAN — Servidor local con múltiples terminales

Esta guía describe cómo operar Softmobile 2025 v2.2.0 en una red local donde un
servidor central expone el backend y varios terminales (POS/operaciones) se
conectan a través de la LAN sin depender de internet.

## Topología recomendada

- **Servidor principal**: equipo con IP fija dentro de la LAN (por ejemplo
  `192.168.0.10`) que ejecuta el backend FastAPI y hospeda la base de datos.
- **Terminales**: navegadores o clientes POS conectados al mismo segmento LAN.
  El frontend se sirve desde el propio servidor (`npm run dev -- --host 0.0.0.0`
  o `npm run build && npm run preview -- --host 0.0.0.0`) y los terminales
  acceden usando la IP del servidor.
- **Base de datos**: SQLite ubicada en el servidor (`/data/softmobile.db`) o
  PostgreSQL local (`postgresql://softmobile:softmobile@192.168.0.10/softmobile`)
  accesible únicamente por la interfaz interna.
- **Red**: se mantiene tráfico HTTP interno (`http://192.168.0.10:8000`) y CORS
  limitado a los dominios/IP de la LAN.

## Descubrimiento y auto-configuración

- **Backend**: el endpoint público `GET /discovery/lan` entrega la IP/puerto
  anunciados y un resumen de la base de datos sin exponer credenciales. Se puede
  desactivar con `SOFTMOBILE_LAN_DISCOVERY_ENABLED=0` o fijar el host con
  `SOFTMOBILE_LAN_HOST` y `SOFTMOBILE_LAN_PORT`.
- **Frontend**: el asistente de configuración LAN en la página de Configuración
  utiliza el endpoint anterior para sugerir la `API_BASE_URL` y almacenarla en el
  navegador, evitando ajustes manuales en cada terminal.

## Flujo operativo

1. Arranca el backend con `uvicorn ... --host 0.0.0.0 --port 8000` en el
   servidor y valida que `DATABASE_URL` apunte al archivo SQLite compartido o a
   PostgreSQL local.
2. Ejecuta el frontend con `npm run dev -- --host 0.0.0.0 --port 5173` (o el
   build estático) y comprueba que los terminales alcanzan la UI vía
   `http://192.168.0.10:5173`.
3. Desde cada terminal, abre el asistente LAN y presiona **Aplicar en este
   navegador** para fijar la API base en `http://192.168.0.10:8000/api`.
4. Verifica la conectividad consultando `/discovery/lan` y los módulos clave
   (inventario, POS, reportes) desde un terminal secundario.

## Consideraciones de base de datos

- **SQLite**: mantén el archivo en un volumen local del servidor. El endpoint de
  descubrimiento indica la ruta real para facilitar respaldos. Evita montarlo en
  carpetas compartidas de red para no corromper el fichero.
- **PostgreSQL**: limita la escucha a la interfaz LAN (`listen_addresses =
  '192.168.0.10'`) y usa usuarios/roles locales. No expongas el puerto a
  internet y configura cortafuegos internos.
- **Respaldo**: programa copias nocturnas en el servidor central y replica el
  archivo SQLite/backup de PostgreSQL en discos externos según la política
  corporativa.
