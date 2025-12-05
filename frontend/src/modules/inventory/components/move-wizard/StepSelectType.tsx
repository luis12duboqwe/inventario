import React from "react";
import { Button } from "@components/ui/Button";

type MoveType = "IN" | "OUT" | "TRANSFER" | "ADJUST";

type Props = {
  value: MoveType;
  onChange: (value: MoveType) => void;
};

export default function StepSelectType({ value, onChange }: Props) {
  const options: MoveType[] = ["IN", "OUT", "TRANSFER", "ADJUST"];

  return (
    <div className="flex gap-2 flex-wrap">
      {options.map((option) => (
        <Button
          key={option}
          variant={value === option ? "primary" : "ghost"}
          onClick={() => onChange(option)}
          type="button"
        >
          {option}
        </Button>
      ))}
    </div>
  );
}
