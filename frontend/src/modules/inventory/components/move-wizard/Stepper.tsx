import React from "react";

type Props = {
  steps: string[];
  active: number;
};

export default function Stepper({ steps, active }: Props) {
  return (
    <div className="flex gap-2 flex-wrap">
      {steps.map((step, index) => (
        <div
          key={`${step}-${index}`}
          className={`px-3 py-1.5 rounded-full text-xs text-white ${
            index === active ? "bg-accent" : "bg-surface-highlight"
          }`}
        >
          {index + 1}. {step}
        </div>
      ))}
    </div>
  );
}
