// [PACK27-EXPORT-DROPDOWN-START]
import { useState } from "react";
import { exportCsvFromItems, exportCsvAll, exportXlsxIfAvailable } from "@/services/exports";

type Props = {
  entity: "customers" | "quotes" | "returns";
  currentItems: any[];
};

export default function ExportDropdown({ entity, currentItems }: Props) {
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);

  function close() {
    setOpen(false);
  }

  async function onCsvPage() {
    exportCsvFromItems(entity, currentItems);
    close();
  }

  async function onCsvAll() {
    setBusy(true);
    try {
      await exportCsvAll(entity);
    } finally {
      setBusy(false);
      close();
    }
  }

  async function onXlsxPage() {
    const ok = await exportXlsxIfAvailable(entity, currentItems);
    close();
    if (!ok) {
      alert("XLSX no disponible (requiere SheetJS). Se recomienda CSV.");
    }
  }

  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <button type="button" onClick={() => setOpen((value) => !value)} disabled={busy}>
        {busy ? "Exportando…" : "Exportar ▾"}
      </button>
      {open && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            background: "#111",
            border: "1px solid #333",
            padding: 8,
            minWidth: 220,
            zIndex: 10,
            display: "grid",
            gap: 4,
          }}
        >
          <button type="button" onClick={onCsvPage} disabled={busy}>
            CSV (esta página)
          </button>
          <button type="button" onClick={onCsvAll} disabled={busy}>
            {busy ? "Exportando…" : "CSV (todo)"}
          </button>
          <button type="button" onClick={onXlsxPage} disabled={busy}>
            XLSX* (esta página)
          </button>
          <div style={{ fontSize: 12, opacity: 0.7, paddingTop: 6 }}>
            * Requiere `XLSX` global. Si no, usa CSV.
          </div>
        </div>
      )}
    </div>
  );
}
// [PACK27-EXPORT-DROPDOWN-END]
