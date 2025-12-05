import React from "react";
import { Button } from "../../../../../components/ui/Button";

type Props = {
  mode: "grid" | "table";
  onChange: (mode: "grid" | "table") => void;
};

export default function ViewSwitch({ mode, onChange }: Props) {
  return (
    <div className="flex gap-2">
      <Button
        variant={mode === "grid" ? "primary" : "ghost"}
        onClick={() => onChange("grid")}
        className="h-8 px-3 text-sm"
      >
        Grid
      </Button>
      <Button
        variant={mode === "table" ? "primary" : "ghost"}
        onClick={() => onChange("table")}
        className="h-8 px-3 text-sm"
      >
        Tabla
      </Button>
    </div>
  );
}
