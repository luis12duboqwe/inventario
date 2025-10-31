import React from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (payload: { tags: string[] }) => void;
};

export default function TagModal({ open, onClose, onSubmit }: Props) {
  const [tags, setTags] = React.useState<string>("");

  if (!open) {
    return null;
  }

  const list = tags
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const valid = list.length > 0;

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "grid", placeItems: "center" }}
    >
      <div
        style={{
          width: 520,
          background: "#0b1220",
          borderRadius: 12,
          border: "1px solid rgba(255,255,255,0.08)",
          padding: 16,
        }}
      >
        <h3 style={{ marginTop: 0 }}>Asignar etiquetas</h3>
        <input
          placeholder="tag1, tag2, tag3"
          value={tags}
          onChange={(event) => setTags(event.target.value)}
          style={{ padding: 8, borderRadius: 8, width: "100%" }}
        />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() => valid && onSubmit?.({ tags: list })}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              background: valid ? "#2563eb" : "rgba(255,255,255,0.08)",
              color: "#fff",
              border: 0,
            }}
          >
            Aplicar
          </button>
        </div>
      </div>
    </div>
  );
}
