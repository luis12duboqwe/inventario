import type { useInventoryModule } from "../../hooks/useInventoryModule";
import type { useSmartImportManager } from "../hooks/useSmartImportManager";

export type InventoryModuleState = ReturnType<typeof useInventoryModule>;
export type SmartImportManagerState = ReturnType<typeof useSmartImportManager>;

export type StatusBadgeTone = "warning" | "success";

export type StatusBadge = {
  tone: StatusBadgeTone;
  text: string;
};

export type StatusCard = {
  id: string;
  title: string;
  caption: string;
  value: string;
  icon: import("lucide-react").LucideIcon;
  badge?: StatusBadge;
};
