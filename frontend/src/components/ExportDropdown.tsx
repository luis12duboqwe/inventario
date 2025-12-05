// [PACK27-EXPORT-DROPDOWN-START]
import { useState } from "react";
import { exportCsvFromItems, exportCsvAll, exportXlsxIfAvailable } from "@/services/exports";
import type { ExportItem } from "@/services/exports";
import { useDashboard } from "@/modules/dashboard/context/DashboardContext";

type Props = {
  entity: "customers" | "quotes" | "returns";
  currentItems: ExportItem[];
};

export default function ExportDropdown({ entity, currentItems }: Props) {
  const { pushToast } = useDashboard();
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
      pushToast("XLSX no disponible (requiere SheetJS). Se recomienda CSV.", "warning");
    }
  }

  return (
    <div className="export-dropdown">
      <button type="button" onClick={() => setOpen((value) => !value)} disabled={busy}>
        {busy ? "Exportando…" : "Exportar ▾"}
      </button>
      {open && (
        <div className="export-dropdown__menu">
          <button type="button" onClick={onCsvPage} disabled={busy}>
            CSV (esta página)
          </button>
          <button type="button" onClick={onCsvAll} disabled={busy}>
            {busy ? "Exportando…" : "CSV (todo)"}
          </button>
          <button type="button" onClick={onXlsxPage} disabled={busy}>
            XLSX* (esta página)
          </button>
          <div className="export-dropdown__hint">* Requiere `XLSX` global. Si no, usa CSV.</div>
        </div>
      )}
    </div>
  );
}
// [PACK27-EXPORT-DROPDOWN-END]
