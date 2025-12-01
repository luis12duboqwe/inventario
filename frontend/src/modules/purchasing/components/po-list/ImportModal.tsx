import React from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (file: File) => void;
  loading?: boolean;
};

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0, 0, 0, 0.5)",
  display: "grid",
  placeItems: "center",
  zIndex: 40,
};

const modalStyle: React.CSSProperties = {
  width: 520,
  background: "#0b1220",
  borderRadius: 12,
  border: "1px solid rgba(255, 255, 255, 0.08)",
  padding: 16,
  boxShadow: "0 18px 40px rgba(15, 23, 42, 0.6)",
};

const buttonStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: 8,
  border: "1px solid rgba(59, 130, 246, 0.4)",
  background: "rgba(37, 99, 235, 0.18)",
  color: "#bfdbfe",
};

export default function ImportModal({ open, onClose, onSubmit, loading = false }: Props) {
  const [file, setFile] = React.useState<File | null>(null);

  if (!open) {
    return null;
  }

  const handleSubmit = () => {
    if (!file || loading) {
      return;
    }
    onSubmit?.(file);
  };

  const handleClose = () => {
    setFile(null);
    onClose?.();
  };

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <h3 style={{ marginTop: 0 }}>Importar PO (CSV/XLSX)</h3>
        <input
          type="file"
          accept=".csv,.xlsx"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.3)" }}
        />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button type="button" onClick={handleClose} style={buttonStyle}>
            Cerrar
          </button>
          <button
            type="button"
            disabled={!file || loading}
            onClick={handleSubmit}
            style={{
              ...buttonStyle,
              background: !file || loading ? "rgba(37, 99, 235, 0.2)" : "#2563eb",
              color: "#fff",
              border: !file || loading ? buttonStyle.border : "0",
              cursor: !file || loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Importando…" : "Subir"}
          </button>
        </div>
      </div>
    </div>
  );
}
