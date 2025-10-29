import React from "react";

export type OrderAttachment = {
  id: string;
  name: string;
  size?: number;
  url?: string;
};

export type OrderAttachmentsProps = {
  items?: OrderAttachment[];
};

function Attachments({ items }: OrderAttachmentsProps) {
  const data = Array.isArray(items) ? items : [];

  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "rgba(255, 255, 255, 0.04)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
        display: "grid",
        gap: 8,
      }}
    >
      <span style={{ fontSize: 12, color: "#94a3b8" }}>Adjuntos</span>
      {data.length === 0 ? (
        <span style={{ color: "#9ca3af" }}>Sin archivos</span>
      ) : (
        <div style={{ display: "grid", gap: 6 }}>
          {data.map((attachment) => (
            <div key={attachment.id} style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
              <span>{attachment.name}</span>
              {attachment.url ? (
                <a href={attachment.url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>
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

export default Attachments;
