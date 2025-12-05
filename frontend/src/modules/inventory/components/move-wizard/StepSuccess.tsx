import React from "react";
import { Button } from "@components/ui/Button";

type Props = {
  number?: string;
  onOpen?: () => void;
};

export default function StepSuccess({ number, onOpen }: Props) {
  return (
    <div className="grid place-items-center gap-4 p-6 rounded-xl bg-surface-highlight border border-border">
      <h3 className="m-0 text-lg font-semibold">¡Movimiento creado!</h3>
      <div className="text-muted-foreground">Número: {number || "—"}</div>
      <Button variant="ghost" onClick={onOpen} type="button">
        Abrir detalle
      </Button>
    </div>
  );
}
