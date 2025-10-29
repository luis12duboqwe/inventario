import React from "react";

type NodeRef = {
  id?: string;
  name?: string;
};

type Props = {
  node?: NodeRef;
};

export default function SourceCard({ node }: Props) {
  const n = node || {};

  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <div style={{ fontSize: 12, color: "#94a3b8" }}>Origen</div>
      <div style={{ fontWeight: 700 }}>{n.name || "—"}</div>
      <div style={{ fontSize: 12, color: "#94a3b8" }}>{n.id || ""}</div>
    </div>
  );
}
