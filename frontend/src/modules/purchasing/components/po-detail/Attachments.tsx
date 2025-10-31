import React from "react";

type FileRef = {
  id: string;
  name: string;
  size?: number;
  url?: string;
};

type Props = {
  items?: FileRef[];
};

const cardStyle: React.CSSProperties = {
  padding: 12,
  borderRadius: 12,
  background: "rgba(255, 255, 255, 0.04)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  display: "grid",
  gap: 8,
};

export default function Attachments({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 12, color: "#94a3b8" }}>Adjuntos</div>
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
