import React from "react";
import { Button } from "@components/ui/Button";

type Props = {
  summary: Record<string, unknown>;
  onSubmit: () => void;
};

export default function StepReview({ summary, onSubmit }: Props) {
  const data = summary || {};

  return (
    <div className="space-y-4">
      <div className="p-4 rounded-xl bg-surface-highlight border border-border">
        <div className="text-xs text-muted-foreground mb-2">Resumen</div>
        <pre className="whitespace-pre-wrap text-sm font-mono">{JSON.stringify(data, null, 2)}</pre>
      </div>
      <div>
        <Button variant="primary" onClick={onSubmit} type="button">
          Crear movimiento
        </Button>
      </div>
    </div>
  );
}
