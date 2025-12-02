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
    <div className="order-attachments-card">
      <span className="order-attachments-label">Adjuntos</span>
      {data.length === 0 ? (
        <span className="order-attachments-empty">Sin archivos</span>
      ) : (
        <div className="order-attachments-list">
          {data.map((attachment) => (
            <div key={attachment.id} className="order-attachment-item">
              <span>{attachment.name}</span>
              {attachment.url ? (
                <a
                  href={attachment.url}
                  target="_blank"
                  rel="noreferrer"
                  className="order-attachment-link"
                >
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
