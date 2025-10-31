import React, { useState } from "react";

type Props = {
  value?: string[];
  onChange: (arr: string[]) => void;
};

const chipStyle: React.CSSProperties = {
  padding: "4px 8px",
  borderRadius: 999,
  background: "rgba(255, 255, 255, 0.08)",
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
};

export default function SerialCapture({ value = [], onChange }: Props) {
  const [current, setCurrent] = useState<string>("");

  const add = () => {
    const trimmed = current.trim();
    if (!trimmed) {
      return;
    }
    onChange([...value, trimmed]);
    setCurrent("");
  };

  const remove = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  return (
    <div style={{ display: "grid", gap: 6 }}>
      <div style={{ display: "flex", gap: 6 }}>
        <input
          placeholder="IMEI/Serial"
          value={current}
          onChange={(event) => setCurrent(event.target.value)}
          style={{ padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }}
        />
        <button type="button" onClick={add} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Agregar
        </button>
      </div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {value.map((serial, index) => (
          <span key={serial + index} style={chipStyle}>
            {serial}
            <button type="button" onClick={() => remove(index)} style={{ border: 0, background: "transparent", color: "#fca5a5" }}>
              ×
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}
