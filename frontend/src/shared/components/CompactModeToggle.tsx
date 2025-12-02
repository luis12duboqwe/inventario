import { type MouseEvent } from "react";
import { Minimize2, Maximize2 } from "lucide-react";

import { useDashboard } from "../../modules/dashboard/context/DashboardContext";
import Button from "@components/ui/Button";

function CompactModeToggle() {
  const { compactMode, toggleCompactMode } = useDashboard();

  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    toggleCompactMode();
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className="compact-toggle"
      onClick={handleClick}
      aria-pressed={compactMode}
      title={compactMode ? "Volver a modo amplio" : "Activar modo compacto"}
      leadingIcon={
        compactMode ? (
          <Maximize2 size={16} aria-hidden="true" />
        ) : (
          <Minimize2 size={16} aria-hidden="true" />
        )
      }
    >
      {compactMode ? "Modo amplio" : "Modo compacto"}
    </Button>
  );
}

export default CompactModeToggle;
