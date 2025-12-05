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

export default function Attachments({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  return (
    <div className="p-3 rounded-xl bg-surface border border-border">
      <div className="text-xs text-muted-foreground mb-2">Adjuntos</div>
      {data.length === 0 ? (
        <div className="text-muted-foreground">Sin archivos</div>
      ) : (
        <div className="grid gap-2">
          {data.map((file) => (
            <div key={file.id} className="flex justify-between">
              <span>{file.name}</span>
              {file.url ? (
                <a
                  href={file.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-primary hover:underline"
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
