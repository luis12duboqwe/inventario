# Guías de configuración de hardware POS

Este documento resume pasos cortos y verificables para preparar los periféricos en tiendas Softmobile 2025 v2.2.0. Sigue las secuencias en orden y registra cada verificación.

## Impresoras de recibos

1. Conecta la impresora al punto de venta (USB o red) y confirma que enciende sin errores en el panel.
2. Define un nombre único en **Configuración POS → Hardware** y selecciona el modo (térmica o fiscal) según el modelo.
3. Ajusta el conector:
   - **USB**: coloca la ruta del puerto (ej. `/dev/usb/lp0`).
   - **Red**: agrega host y puerto (9100 por defecto) y valida ping desde la caja.
4. Establece el ancho de papel (80 mm por defecto) y guarda los cambios.
5. Ejecuta **Probar impresión** para generar el recibo de diagnóstico; si falla, revisa drivers y permisos del usuario de caja.

## Gavetas de efectivo

1. Activa la opción **Habilitar apertura automática** en Hardware POS.
2. Define el identificador de la gaveta y el tipo de conector (USB o red) con sus parámetros (host/puerto si aplica).
3. Ajusta la duración del pulso (100–200 ms suele ser suficiente) y guarda.
4. Presiona **Abrir gaveta** y confirma que se dispare el mecanismo sin bloquear otras tareas de caja.
5. Si la prueba falla, revisa el cable RJ11 hacia la impresora o la fuente de alimentación de la gaveta.

## Pantallas de cliente

1. Habilita **Pantalla de cliente** y elige el canal (WebSocket para remoto o Local para kioskos en la misma caja).
2. Establece encabezado, mensaje y tema (oscuro recomendado) y ajusta el brillo al entorno.
3. Incluye el total mostrado solo si deseas validar el cálculo; deja en blanco para mensajes generales.
4. Ejecuta **Probar pantalla** y verifica que el mensaje aparezca legible y sin recortes.
5. Si no se refleja, revisa el websocket o el servicio local del display y reintenta con un mensaje corto.

## Lectores de códigos de barras

1. Conecta el lector en modo teclado (USB) y abre la utilidad de diagnóstico en el frontend.
2. Coloca el cursor en el campo de prueba y escanea un código conocido.
3. Confirma que el valor aparezca completo sin caracteres extra ni saltos de línea adicionales.
4. Repite con dos códigos más para validar velocidad y consistencia.
5. Si falla, revisa el modo del lector (HID/Serial), la distribución del teclado y desactiva sufijos de tabulación.

## Checklist de instalación para partners locales

- [ ] La sucursal tiene internet estable o red local funcional para el hardware configurado.
- [ ] Se documentó el nombre del dispositivo, tipo de conector y puerto/host para impresoras y gavetas.
- [ ] Las pruebas de impresión, apertura de gaveta y mensaje en pantalla cliente se ejecutaron con éxito.
- [ ] Se registraron tres lecturas consecutivas de código de barras sin errores ni duplicados.
- [ ] Las credenciales de acceso y el motivo corporativo (`X-Reason`) están definidos para futuros diagnósticos.
- [ ] Se dejó evidencia (foto o PDF) del recibo de prueba y de la pantalla de cliente mostrando el mensaje de diagnóstico.
- [ ] El partner confirmó el horario de soporte y el procedimiento de escalamiento ante fallos de hardware.
