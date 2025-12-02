import React from "react";

export type POSAmountPadProps = {
  value: number;
  onChange: (value: number) => void;
};

const DIGITS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0];

function AmountPad({ value, onChange }: POSAmountPadProps) {
  const handleAppend = (digit: number) => {
    const next = Number(((value ?? 0) * 10 + digit).toFixed(2));
    onChange(next);
  };

  const handleClear = () => {
    onChange(0);
  };

  return (
    <div className="pos-amount-pad">
      {DIGITS.map((digit) => (
        <button key={digit} onClick={() => handleAppend(digit)} className="pos-amount-pad-btn">
          {digit}
        </button>
      ))}
      <button onClick={handleClear} className="pos-amount-pad-btn-clear">
        Limpiar
      </button>
    </div>
  );
}

export default AmountPad;
