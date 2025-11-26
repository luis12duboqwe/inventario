# Flujo de generación de reportes globales v2.2.0

La capa de reportes globales ahora se divide en dos niveles claramente definidos:

1. **Datos (`backend/app/services/global_reports_data.py`)**
   - Expone los DTO `GlobalReportDataset`, `get_overview`, `get_dashboard` y `build_dataset`.
   - Centraliza las llamadas a `crud.build_global_report_*` aplicando los filtros recibidos.
   - Garantiza estructuras inmutables listas para que cualquier renderizador genere archivos sin repetir consultas.

2. **Renderizadores (`backend/app/services/global_reports_renderers.py`)**
   - Renderiza PDF, Excel y CSV a partir de los DTO anteriores.
   - Reutiliza las constantes corporativas definidas en `backend/app/services/global_reports_constants.py` para asegurar la identidad visual (`#0f172a`, `#111827`, acento `#38bdf8`).

El router `backend/app/routers/reports.py` consume primero `build_dataset` y, según el parámetro `format`, delega en el renderizador correspondiente. Las pruebas `backend/tests/test_global_reports.py` validan la obtención del dataset y cada renderizador para mantener la compatibilidad retroactiva.
