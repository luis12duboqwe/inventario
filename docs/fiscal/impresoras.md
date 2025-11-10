# Impresoras fiscales locales — Integración Softmobile v2.2.0

## Objetivo

Las sucursales ahora pueden definir impresoras fiscales con perfiles técnicos
propios, reutilizando los SDK locales Hasar (`pyhasar`), Epson (`pyfiscalprinter`)
y Bematech (`bemafiscal`). Cuando el SDK no está disponible o se activa el modo
de simulación, el sistema ejecuta la misma secuencia de comandos y registra la
razón del modo simulado para facilitar auditorías.

## Configuración por sucursal

Cada impresora en `POSConfig.hardware_settings.printers` admite el bloque
`fiscal_profile`. Este perfil controla:

- `adapter`: `hasar`, `epson`, `bematech` o `simulated`.
- `sdk_module`: módulo Python alterno (opcional, se infiere por defecto).
- `taxpayer_id`, `serial_number`, `model` y `document_type`.
- `timeout_s`, `simulate_only` y `extra_settings` para parámetros específicos
  (por ejemplo, caja asignada o códigos tributarios locales).

Ejemplo JSON incluido en `tests/test_pos.py::test_pos_fiscal_printer_prints_sequence`:

```json
{
  "name": "HASAR-01",
  "mode": "fiscal",
  "connector": {
    "type": "network",
    "identifier": "HASAR-01",
    "host": "192.168.1.50",
    "port": 9100
  },
  "fiscal_profile": {
    "adapter": "hasar",
    "taxpayer_id": "RTN123456789",
    "serial_number": "H001-XYZ",
    "model": "PR5F",
    "document_type": "ticket",
    "extra_settings": {"caja": "1"}
  }
}
```

## Adaptadores incluidos

El módulo `backend/app/services/hardware/fiscal_printers.py` registra cuatro
adaptadores:

| Adaptador  | SDK sugerido       | Comandos enviados                                           |
|------------|--------------------|--------------------------------------------------------------|
| `hasar`    | `pyhasar`          | `ABRIR_COMPROBANTE`, `IMPRIMIR_TEXTO`, `CERRAR_COMPROBANTE` |
| `epson`    | `pyfiscalprinter`  | `open_fiscal_receipt`, `print_line`, `close_receipt`        |
| `bematech` | `bemafiscal`       | `abreCupom`, `vendeItem`, `fechaCupom`                      |
| `simulated`| — (sin SDK)        | Secuencia genérica con anotación `Simulación de impresora fiscal` |

Todos los adaptadores construyen el contexto del conector (USB o red) y capturan
la metadata del perfil (serie, RTN, modelo, etc.). Si el SDK no está instalado
o el perfil solicita `simulate_only`, el comando devuelve `sdk_missing` o
`simulate_only` como motivo del modo simulado.

## Flujo de comandos

`ReceiptPrinterService` utiliza el perfil fiscal para componer una secuencia de
apertura, línea de texto y cierre. El resultado expuesto por
`POST /pos/hardware/print-test` incluye:

- `adapter`: adaptador utilizado.
- `commands`: lista de comandos con metadata, módulo SDK y bandera `simulated`.
- `simulated`: `true` cuando no se ejecutó el SDK real.

Esto garantiza trazabilidad completa del documento fiscal y permite enviar la
misma secuencia desde los agentes locales que consumen el canal WebSocket.

## Pruebas

Se añadieron dos pruebas clave:

1. `tests/test_pos.py::test_pos_fiscal_printer_prints_sequence` valida el flujo
   completo vía API, confirmando que la sucursal recibe comandos fiscales en
   orden y en modo simulado por ausencia del SDK.
2. `tests/test_fiscal_printers.py::test_fiscal_printer_registry_simulation_when_sdk_missing`
   ejecuta el adaptador de Hasar directamente y comprueba que la secuencia se
   marca como simulada y documenta el adaptador en la metadata.

Ambas pruebas se ejecutan dentro de `pytest` y no requieren dependencias
externas, de modo que pueden ejecutarse en entornos CI sin hardware conectado.
