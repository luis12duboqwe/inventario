import { FileSpreadsheet, FileText } from "lucide-react";

type ToolbarContentProps = {
  onExportPdf: () => void;
  onExportExcel: () => void;
  disabled: boolean;
  error?: string | null;
};

function Toolbar({ onExportPdf, onExportExcel, disabled, error }: ToolbarContentProps) {
  return (
    <>
      <header className="card-header">
        <div>
          <h2>Gestión de usuarios</h2>
          <p className="card-subtitle">
            Administra cuentas corporativas, roles asignados, motivos de inactivación y permisos por módulo.
          </p>
        </div>
        <div className="export-buttons">
          <button type="button" className="button button-secondary" onClick={onExportPdf} disabled={disabled}>
            <FileText size={16} aria-hidden="true" />
            PDF
          </button>
          <button type="button" className="button button-secondary" onClick={onExportExcel} disabled={disabled}>
            <FileSpreadsheet size={16} aria-hidden="true" />
            Excel
          </button>
        </div>
      </header>
      {error ? <p className="error-text">{error}</p> : null}
    </>
  );
}

export type UsersToolbarProps = ToolbarContentProps;

export default Toolbar;
