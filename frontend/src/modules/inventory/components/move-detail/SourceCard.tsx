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
    <div className="p-3 rounded-xl bg-surface border border-border">
      <div className="text-xs text-muted-foreground">Origen</div>
      <div className="font-bold">{n.name || "—"}</div>
      <div className="text-xs text-muted-foreground">{n.id || ""}</div>
    </div>
  );
}
