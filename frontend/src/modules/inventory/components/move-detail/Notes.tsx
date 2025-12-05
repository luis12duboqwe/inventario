import React from "react";

type Props = {
  value?: string;
};

export default function Notes({ value }: Props) {
  return (
    <div className="p-3 rounded-xl bg-surface border border-border">
      <div className="text-xs text-muted-foreground mb-2">Notas</div>
      <div className="whitespace-pre-wrap">{value || "—"}</div>
    </div>
  );
}
