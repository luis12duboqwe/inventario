// [PACK27-EXPORTS-SVC-START]
import { downloadText } from "@/lib/download";
import { toCsv } from "@/lib/csv";
import { SalesCustomers, SalesQuotes, SalesReturns } from "@/services/sales";
import { formatCurrencyWithUsd, formatDateHn } from "@/utils/locale";
import type { Customer, Quote, ReturnDoc } from "./sales/types";

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
  return formatDateHn(date);
}

function formatCurrency(value?: number | null): string {
  if (typeof value !== "number") return "";
  return formatCurrencyWithUsd(value);
}

export type ExportEntity = "customers" | "quotes" | "returns";
export type ExportItem = Customer | Quote | ReturnDoc;

interface ColumnDef<T> {
  key: keyof T | string;
  title: string;
  map?: (v: unknown) => string | number;
}

interface QuoteTotals {
  grand: number;
}

interface WindowWithXLSX extends Window {
  XLSX?: {
    utils: {
      json_to_sheet: (data: unknown[]) => unknown;
      book_new: () => unknown;
      book_append_sheet: (wb: unknown, ws: unknown, name: string) => void;
    };
    writeFile: (wb: unknown, filename: string) => void;
  };
}

// Descarga CSV de la página actual (recibe items ya renderizados)
export function exportCsvFromItems(entity: ExportEntity, items: ExportItem[]) {
  let cols: ColumnDef<unknown>[] = [];
  if (entity === "customers") {
    cols = [
      { key: "name", title: "Nombre" },
      { key: "phone", title: "Teléfono" },
      { key: "email", title: "Email" },
      { key: "tier", title: "Tier" },
      { key: "createdAt", title: "Creado", map: (v) => formatDate(v as string) },
    ];
  } else if (entity === "quotes") {
    cols = [
      { key: "number", title: "Número" },
      { key: "date", title: "Fecha", map: (v) => formatDate(v as string) },
      { key: "status", title: "Estado", map: (v) => quoteStatusLabels[String(v)] ?? String(v) },
      { key: "customerName", title: "Cliente" },
      { key: "totals", title: "Total", map: (v) => formatCurrency((v as QuoteTotals)?.grand) },
    ];
  } else if (entity === "returns") {
    cols = [
      { key: "number", title: "Número" },
      { key: "date", title: "Fecha", map: (v) => formatDate(v as string) },
      { key: "reason", title: "Motivo", map: (v) => returnReasonLabels[String(v)] ?? String(v) },
      { key: "customerName", title: "Cliente" },
      { key: "totalCredit", title: "Total", map: (v) => formatCurrency(v as number) },
    ];
  }
  const csv = toCsv(items as unknown as Record<string, unknown>[], cols);
  downloadText(csv, `${entity}-${new Date().toISOString().slice(0, 10)}.csv`, "text/csv;charset=utf-8");
}

// Descarga CSV de TODO el dataset (paginando desde el service)
export async function exportCsvAll(entity: ExportEntity) {
  const pageSize = 200;
  let page = 1;
  const all: ExportItem[] = [];
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
export async function exportXlsxIfAvailable(entity: ExportEntity, items: ExportItem[]) {
  const XLSX = (window as unknown as WindowWithXLSX).XLSX ?? undefined;
  if (!XLSX) return false;
  const ws = XLSX.utils.json_to_sheet(items);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, entity);
  XLSX.writeFile(wb, `${entity}-${new Date().toISOString().slice(0, 10)}.xlsx`);
  return true;
}
// [PACK27-EXPORTS-SVC-END]
