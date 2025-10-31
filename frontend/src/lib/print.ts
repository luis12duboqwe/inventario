// [PACK27-PRINT-UTILS-START]
import { openUrlNewTab, downloadText } from "@/lib/download";

/** Abre el PDF si viene por URL; si viene HTML, abre ventana imprimible; si viene texto plano, descarga. */
export function openPrintable(
  printable?: { pdfUrl?: string; html?: string; plain?: string } | null,
  fallbackName = "documento",
) {
  if (!printable) return;
  if (printable.pdfUrl) return openUrlNewTab(printable.pdfUrl);
  if (printable.html) {
    const w = window.open("", "_blank", "noopener,noreferrer,width=900,height=700");
    if (!w) return;
    w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${fallbackName}</title>
      <style>
        @media print { @page { margin: 10mm; } body { -webkit-print-color-adjust: exact; } }
        body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; padding: 16px; color: #111; }
        h1,h2,h3 { margin: 0 0 8px 0; }
        table { width: 100%; border-collapse: collapse; }
        td, th { border: 1px solid #ddd; padding: 6px 8px; font-size: 12px; }
        tfoot td { font-weight: 600; }
      </style>
    </head><body>${printable.html}</body></html>`);
    w.document.close();
    setTimeout(() => w.print(), 350);
    return;
  }
  if (printable.plain) return downloadText(printable.plain, `${fallbackName}.txt`);
}
// [PACK27-PRINT-UTILS-END]
