import React from "react";

type MoveType = "IN" | "OUT" | "TRANSFER" | "ADJUST";

type Props = {
  value: MoveType;
  onChange: (value: MoveType) => void;
};

export default function StepSelectType({ value, onChange }: Props) {
  const options: MoveType[] = ["IN", "OUT", "TRANSFER", "ADJUST"];

  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {options.map((option) => (
        <button
          key={option}
          onClick={() => onChange(option)}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            background: value === option ? "#2563eb" : "rgba(255,255,255,0.08)",
            color: "#fff",
            border: 0,
          }}
          type="button"
        >
          {option}
        </button>
      ))}
    </div>
  );
}
