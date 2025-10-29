import React from "react";

export type POSAmountPadProps = {
  value: number;
  onChange: (value: number) => void;
};

const DIGITS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0];

function AmountPad({ value, onChange }: POSAmountPadProps) {
  const handleAppend = (digit: number) => {
    const next = Number((((value ?? 0) * 10 + digit)).toFixed(2));
    onChange(next);
  };

  const handleClear = () => {
    onChange(0);
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
      {DIGITS.map((digit) => (
        <button key={digit} onClick={() => handleAppend(digit)} style={{ padding: "12px 0", borderRadius: 8 }}>
          {digit}
        </button>
      ))}
      <button onClick={handleClear} style={{ padding: "12px 0", borderRadius: 8, gridColumn: "span 3" }}>
        Limpiar
      </button>
    </div>
  );
}

export default AmountPad;
