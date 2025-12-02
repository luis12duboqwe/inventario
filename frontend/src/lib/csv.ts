// [PACK27-CSV-START]
function escapeCsvCell(v: unknown): string {
  if (v === null || typeof v === "undefined") return "";
  const s = String(v);
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

export function toCsv(
  rows: Record<string, unknown>[],
  columns: { key: string; title: string; map?: (value: unknown) => unknown }[],
): string {
  const header = columns.map((column) => escapeCsvCell(column.title)).join(",");
  const data = rows
    .map((row) =>
      columns
        .map((column) => {
          const raw = row?.[column.key];
          const mapped = column.map ? column.map(raw) : raw;
          return escapeCsvCell(mapped);
        })
        .join(","),
    )
    .join("\n");
  return `${header}\n${data}\n`;
}
// [PACK27-CSV-END]
