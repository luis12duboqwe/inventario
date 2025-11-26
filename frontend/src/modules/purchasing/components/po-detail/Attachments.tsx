import React, { useRef } from "react";

type FileRef = {
  id: string;
  name: string;
  size?: number;
  url?: string;
};

type Props = {
  items?: FileRef[];
  onUpload?: (file: File) => void;
  uploading?: boolean;
};

const cardStyle: React.CSSProperties = {
  padding: 12,
  borderRadius: 12,
  background: "rgba(255, 255, 255, 0.04)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  display: "grid",
  gap: 8,
};

export default function Attachments({ items, onUpload, uploading }: Props) {
  const data = Array.isArray(items) ? items : [];
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleSelectFile = () => {
    if (!onUpload) {
      return;
    }
    inputRef.current?.click();
  };

  const handleFileChange: React.ChangeEventHandler<HTMLInputElement> = (event) => {
    if (!onUpload) {
      return;
    }
    const file = event.target.files?.[0];
    if (file) {
      onUpload(file);
      event.target.value = "";
    }
  };

  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 12, color: "#94a3b8" }}>Adjuntos</div>
      {onUpload ? (
        <>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            onChange={handleFileChange}
            style={{ display: "none" }}
          />
          <button
            type="button"
            onClick={handleSelectFile}
            disabled={uploading}
            style={{
              padding: "6px 10px",
              borderRadius: 8,
              background: "rgba(37, 99, 235, 0.18)",
              color: "#bfdbfe",
              border: "1px solid rgba(59, 130, 246, 0.4)",
              cursor: uploading ? "not-allowed" : "pointer",
              opacity: uploading ? 0.5 : 1,
            }}
          >
            {uploading ? "Subiendo…" : "Subir PDF"}
          </button>
        </>
      ) : null}
      {data.length === 0 ? (
        <div style={{ color: "#9ca3af" }}>Sin archivos</div>
      ) : (
        <div style={{ display: "grid", gap: 6 }}>
          {data.map((file) => (
            <div key={file.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>{file.name}</span>
              {file.url ? (
                <a href={file.url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>
                  Ver
                </a>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
