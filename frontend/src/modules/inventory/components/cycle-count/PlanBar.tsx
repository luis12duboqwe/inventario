type Plan = {
  warehouse?: string;
  area?: string;
  families?: string;
  frequency?: "DAILY" | "WEEKLY" | "MONTHLY" | "CUSTOM";
};

type Props = {
  value: Plan;
  onChange: (value: Plan) => void;
  onStart?: () => void;
};

const frequencies: Array<{ value: Plan["frequency"]; label: string }> = [
  { value: "DAILY", label: "Diario" },
  { value: "WEEKLY", label: "Semanal" },
  { value: "MONTHLY", label: "Mensual" },
  { value: "CUSTOM", label: "Personalizado" },
];

function PlanBar({ value, onChange, onStart }: Props) {
  return (
    <div className="inventory-filters-grid">
      <input
        placeholder="Almacén"
        value={value.warehouse ?? ""}
        onChange={(event) => onChange({ ...value, warehouse: event.target.value })}
      />
      <input
        placeholder="Área/Zona"
        value={value.area ?? ""}
        onChange={(event) => onChange({ ...value, area: event.target.value })}
      />
      <input
        placeholder="Familias (CSV)"
        value={value.families ?? ""}
        onChange={(event) => onChange({ ...value, families: event.target.value })}
      />
      <select
        value={value.frequency ?? "WEEKLY"}
        onChange={(event) => onChange({ ...value, frequency: event.target.value as Plan["frequency"] })}
      >
        {frequencies.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <button type="button" className="primary" onClick={onStart}>
        Iniciar
      </button>
    </div>
  );
}

export type { Plan as CyclePlan };
export default PlanBar;
