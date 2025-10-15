import { type MouseEvent } from "react";
import { Minimize2, Maximize2 } from "lucide-react";

import { useDashboard } from "../modules/dashboard/context/DashboardContext";

function CompactModeToggle() {
  const { compactMode, toggleCompactMode } = useDashboard();

  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    toggleCompactMode();
  };

  return (
    <button
      type="button"
      className="btn btn--ghost compact-toggle"
      onClick={handleClick}
      aria-pressed={compactMode}
      title={compactMode ? "Volver a modo amplio" : "Activar modo compacto"}
    >
      <span className="compact-toggle__icon" aria-hidden="true">
        {compactMode ? <Maximize2 size={16} /> : <Minimize2 size={16} />}
      </span>
      <span>{compactMode ? "Modo amplio" : "Modo compacto"}</span>
    </button>
  );
}

export default CompactModeToggle;
