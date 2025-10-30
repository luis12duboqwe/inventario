// [PACK27-EXPORTS-SVC-START]
import { downloadText } from "@/lib/download";
import { toCsv } from "@/lib/csv";
import { SalesCustomers, SalesQuotes, SalesReturns } from "@/services/sales";

const quoteStatusLabels: Record<string, string> = {
  OPEN: "Abierta",
  APPROVED: "Aprobada",
  EXPIRED: "Expirada",
  CONVERTED: "Convertida",
};

const returnReasonLabels: Record<string, string> = {
  DEFECT: "Defecto",
  BUYER_REMORSE: "Remordimiento",
  WARRANTY: "Garantía",
  OTHER: "Otro",
};

function formatDate(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
}

function formatCurrency(value?: number | null): string {
  if (typeof value !== "number") return "";
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(value);
}

// Descarga CSV de la página actual (recibe items ya renderizados)
export function exportCsvFromItems(entity: "customers" | "quotes" | "returns", items: any[]) {
  let cols: { key: string; title: string; map?: (v: any) => any }[] = [];
  if (entity === "customers") {
    cols = [
      { key: "name", title: "Nombre" },
      { key: "phone", title: "Teléfono" },
      { key: "email", title: "Email" },
      { key: "tier", title: "Tier" },
      { key: "createdAt", title: "Creado", map: (v) => formatDate(v) },
    ];
  } else if (entity === "quotes") {
    cols = [
      { key: "number", title: "Número" },
      { key: "date", title: "Fecha", map: (v) => formatDate(v) },
      { key: "status", title: "Estado", map: (v) => quoteStatusLabels[String(v)] ?? v },
      { key: "customerName", title: "Cliente" },
      { key: "totals", title: "Total", map: (v) => formatCurrency(v?.grand) },
    ];
  } else if (entity === "returns") {
    cols = [
      { key: "number", title: "Número" },
      { key: "date", title: "Fecha", map: (v) => formatDate(v) },
      { key: "reason", title: "Motivo", map: (v) => returnReasonLabels[String(v)] ?? v },
      { key: "customerName", title: "Cliente" },
      { key: "totalCredit", title: "Total", map: (v) => formatCurrency(v) },
    ];
  }
  const csv = toCsv(items, cols);
  downloadText(csv, `${entity}-${new Date().toISOString().slice(0, 10)}.csv`, "text/csv;charset=utf-8");
}

// Descarga CSV de TODO el dataset (paginando desde el service)
export async function exportCsvAll(entity: "customers" | "quotes" | "returns") {
  const pageSize = 200;
  let page = 1;
  const all: any[] = [];
  let total = 0;
  while (true) {
    if (entity === "customers") {
      const res = await SalesCustomers.listCustomers({ page, pageSize });
      all.push(...(res.items || []));
      total = res.total || 0;
    } else if (entity === "quotes") {
      const res = await SalesQuotes.listQuotes({ page, pageSize });
      all.push(...(res.items || []));
      total = res.total || 0;
    } else if (entity === "returns") {
      const res = await SalesReturns.listReturns({ page, pageSize });
      all.push(...(res.items || []));
      total = res.total || 0;
    }
    if (all.length >= total || (all.length && all.length % pageSize !== 0)) break;
    page += 1;
    if (page > 10000) break; // guard
  }
  exportCsvFromItems(entity, all);
}

// XLSX (opcional) si ya existe SheetJS
export async function exportXlsxIfAvailable(entity: "customers" | "quotes" | "returns", items: any[]) {
  // @ts-ignore
  const XLSX = (window as any).XLSX ?? undefined;
  if (!XLSX) return false;
  const ws = XLSX.utils.json_to_sheet(items);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, entity);
  XLSX.writeFile(wb, `${entity}-${new Date().toISOString().slice(0, 10)}.xlsx`);
  return true;
}
// [PACK27-EXPORTS-SVC-END]
