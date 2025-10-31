const reasons = [
  "DAMAGE",
  "THEFT",
  "WRITE_OFF",
  "INITIAL_BALANCE",
  "CORRECTION",
  "LOST_FOUND",
] as const;

type Props = {
  value: string;
  onChange: (value: string) => void;
};

function ReasonSelector({ value, onChange }: Props) {
  return (
    <div className="chip-group">
      {reasons.map((reason) => (
        <button
          key={reason}
          type="button"
          className={`chip ${value === reason ? "chip--active" : ""}`}
          onClick={() => onChange(reason)}
        >
          {reason}
        </button>
      ))}
    </div>
  );
}

export default ReasonSelector;
