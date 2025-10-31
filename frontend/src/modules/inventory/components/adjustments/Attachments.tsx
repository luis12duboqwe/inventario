import type { ChangeEvent } from "react";

export type AttachmentItem = {
  id: string;
  name: string;
  size?: number;
  uploadedAt?: string;
  url?: string;
};

type Props = {
  items?: AttachmentItem[];
  onUpload?: (files: FileList) => void;
  onRemove?: (id: string) => void;
  onPreview?: (item: AttachmentItem) => void;
};

function formatSize(size?: number): string {
  if (!size || Number.isNaN(size)) {
    return "";
  }
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function Attachments({ items, onUpload, onRemove, onPreview }: Props) {
  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      onUpload?.(event.target.files);
      event.target.value = "";
    }
  };

  const list = Array.isArray(items) ? items : [];

  return (
    <section className="attachments-card">
      <header className="attachments-card__header">
        <h4>Adjuntos</h4>
        <label className="button ghost">
          Subir archivos
          <input type="file" multiple onChange={handleFileChange} hidden />
        </label>
      </header>
      {list.length === 0 ? (
        <p className="muted">Sin archivos adjuntos</p>
      ) : (
        <ul className="attachments-card__list">
          {list.map((item) => (
            <li key={item.id}>
              <div>
                <strong>{item.name}</strong>
                <span>{formatSize(item.size)}</span>
                {item.uploadedAt ? <time>{new Date(item.uploadedAt).toLocaleString()}</time> : null}
              </div>
              <div className="attachments-card__actions">
                <button type="button" className="ghost" onClick={() => onPreview?.(item)}>
                  Ver
                </button>
                <button type="button" className="danger" onClick={() => onRemove?.(item.id)}>
                  Eliminar
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default Attachments;
