import { useCallback } from "react";
import QRCode from "qrcode";
import { emitClientError } from "@/utils/clientLog";
import { useDashboard } from "@/modules/dashboard/context/DashboardContext";
import { colors } from "@/theme/designTokens";
import { Device } from "@api/inventory";
import { formatCurrencyHnl } from "@/utils/locale";

export type PrintOptions = {
  includePrice: boolean;
  includeLogo: boolean;
  labelSize: "small" | "medium" | "large";
  template?: "standard" | "price_tag" | "inventory_tag";
};

export function useLabelPrinter() {
  const { pushToast } = useDashboard();

  const escapeHtml = useCallback((value: string) => {
    return value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }, []);

  const generateLabelHtml = useCallback(async (device: Device, options: PrintOptions) => {
      const qrPayload = JSON.stringify({
        sku: device.sku,
        imei: device.imei ?? null,
        serial: device.serial ?? null,
      });

      let dataUrl: string;
      try {
        dataUrl = await QRCode.toDataURL(qrPayload, {
          width: 160,
          margin: 1,
          errorCorrectionLevel: "M",
        });
      } catch (error) {
        console.error("Error generating QR", error);
        return null;
      }

      const modelLabel = escapeHtml(device.modelo ?? device.name);
      const skuLabel = escapeHtml(device.sku);
      const imeiLabel = device.imei ? escapeHtml(device.imei) : "—";
      const priceLabel = options.includePrice && device.precio_venta ? formatCurrencyHnl(device.precio_venta) : null;
      const template = options.template || "standard";

      // Size configurations
      const sizeConfig = {
          small: { width: '50mm', height: '25mm', fontSize: '10px', qrSize: '40px' },
          medium: { width: '70mm', height: '35mm', fontSize: '12px', qrSize: '60px' },
          large: { width: '100mm', height: '50mm', fontSize: '14px', qrSize: '80px' }
      }[options.labelSize];

      let contentHtml = '';

      if (template === "price_tag") {
        // Price Tag Template: Big Price, Small Name
        contentHtml = `
            <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;">
                ${options.includeLogo ? `<div style="font-weight: bold; font-size: ${parseInt(sizeConfig.fontSize) - 2}px; color: #000; margin-bottom: 2px;">SOFTMOBILE</div>` : ''}
                <div style="font-size: ${sizeConfig.fontSize}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;">${modelLabel}</div>
                ${priceLabel ? `<div style="font-weight: 900; font-size: ${parseInt(sizeConfig.fontSize) * 2}px; margin: 4px 0;">${priceLabel}</div>` : ''}
                <div style="font-size: ${parseInt(sizeConfig.fontSize) - 2}px;">SKU: ${skuLabel}</div>
            </div>
        `;
      } else if (template === "inventory_tag") {
        // Inventory Tag Template: Big SKU/IMEI, Big QR
        contentHtml = `
            <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; padding-right: 4px;">
                <div style="font-weight: bold; font-size: ${parseInt(sizeConfig.fontSize) + 2}px;">SKU: ${skuLabel}</div>
                ${device.imei ? `<div style="font-weight: bold; font-size: ${sizeConfig.fontSize}; margin-top: 4px;">IMEI: ${imeiLabel}</div>` : ''}
                <div style="font-size: ${parseInt(sizeConfig.fontSize) - 2}px; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${modelLabel}</div>
            </div>
            <div style="width: ${sizeConfig.qrSize}; height: ${sizeConfig.qrSize}; display: flex; align-items: center; justify-content: center; align-self: center;">
                <img src="${dataUrl}" style="width: 100%; height: 100%; object-fit: contain;" />
            </div>
        `;
      } else {
        // Standard Template
        contentHtml = `
            <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; padding-right: 4px;">
                ${options.includeLogo ? `<div style="font-weight: bold; font-size: ${sizeConfig.fontSize}; color: #000; margin-bottom: 2px;">SOFTMOBILE</div>` : ''}
                <div style="font-weight: bold; font-size: ${sizeConfig.fontSize}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${modelLabel}</div>
                <div style="font-size: ${parseInt(sizeConfig.fontSize) - 2}px;">SKU: ${skuLabel}</div>
                ${device.imei ? `<div style="font-size: ${parseInt(sizeConfig.fontSize) - 3}px;">IMEI: ${imeiLabel}</div>` : ''}
                ${priceLabel ? `<div style="font-weight: bold; font-size: ${sizeConfig.fontSize}; margin-top: 2px;">${priceLabel}</div>` : ''}
            </div>
            <div style="width: ${sizeConfig.qrSize}; height: ${sizeConfig.qrSize}; display: flex; align-items: center; justify-content: center; align-self: center;">
                <img src="${dataUrl}" style="width: 100%; height: 100%; object-fit: contain;" />
            </div>
        `;
      }

      return `
        <div class="label" style="width: ${sizeConfig.width}; height: ${sizeConfig.height}; page-break-inside: avoid; display: flex; border: 1px solid #eee; padding: 4px; box-sizing: border-box; overflow: hidden; position: relative; margin-bottom: 2mm; margin-right: 2mm;">
            ${contentHtml}
        </div>
      `;
  }, [escapeHtml]);

  const handlePrintLabels = useCallback(
    async (devices: Device[], options: PrintOptions = { includePrice: true, includeLogo: true, labelSize: "medium", template: "standard" }) => {

      const labelsHtmlPromises = devices.map(d => generateLabelHtml(d, options));
      const labelsHtml = (await Promise.all(labelsHtmlPromises)).filter(Boolean).join('');

      if (!labelsHtml) {
          pushToast({ message: "No se pudieron generar las etiquetas", variant: "error" });
          return;
      }

      const printWindow = window.open("", "softmobile-print-label", "width=800,height=600");
      if (!printWindow) {
        pushToast({
          message: "Debes permitir ventanas emergentes para imprimir la etiqueta.",
          variant: "warning",
        });
        return;
      }

      const html = `<!DOCTYPE html>
<html lang="es">
  <head>
    <meta charSet="utf-8" />
    <title>Imprimir Etiquetas</title>
    <style>
      @page { margin: 0; }
      body { margin: 0; padding: 10mm; font-family: sans-serif; }
      .label-container { display: flex; flex-wrap: wrap; align-content: flex-start; }
      @media print {
          .label { border: none !important; }
      }
    </style>
  </head>
  <body>
    <div class="label-container">
        ${labelsHtml}
    </div>
    <script>
      window.onload = () => {
          window.print();
          // setTimeout(() => window.close(), 500); // Keep open for debug if needed
      };
    </script>
  </body>
</html>`;

      printWindow.document.open();
      printWindow.document.write(html);
      printWindow.document.close();
    },
    [generateLabelHtml, pushToast],
  );

  return { handlePrintLabels };
}
