import { useState } from "react";

type Props = {
  onAdd: (imei: string) => void;
};

function ScanIMEI({ onAdd }: Props) {
  const [value, setValue] = useState<string>("");

  const handleAdd = () => {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    onAdd(trimmed);
    setValue("");
  };

  return (
    <div className="scan-bar">
      <input
        placeholder="Escanear IMEI/serial"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            handleAdd();
          }
        }}
      />
      <button type="button" className="primary" onClick={handleAdd}>
        Agregar
      </button>
    </div>
  );
}

export default ScanIMEI;
