import type { RepairOrder } from "../../../../api";

import type { RepairForm } from "../../../../types/repairs";

type RepairVisual = {
  icon: string;
  imageUrl?: string;
};

const VISUAL_STORAGE_KEY = "softmobile:repair-visuals";

const repairStatusLabels: Record<RepairOrder["status"], string> = {
  PENDIENTE: "🟡 Pendiente",
  EN_PROCESO: "🟠 En proceso",
  LISTO: "🟢 Listo",
  ENTREGADO: "⚪ Entregado",
};

const repairStatusOptions: Array<RepairOrder["status"]> = [
  "PENDIENTE",
  "EN_PROCESO",
  "LISTO",
  "ENTREGADO",
];

const initialRepairForm: RepairForm = {
  storeId: null,
  customerId: null,
  customerName: "",
  technicianName: "",
  damageType: "",
  deviceDescription: "",
  notes: "",
  laborCost: 0,
  parts: [],
};

const resolveDamageIcon = (damageType: string): string => {
  const normalized = damageType.toLowerCase();
  if (normalized.includes("pantalla") || normalized.includes("display")) {
    return "📱";
  }
  if (normalized.includes("bater")) {
    return "🔋";
  }
  if (normalized.includes("puerto") || normalized.includes("carga")) {
    return "🔌";
  }
  if (normalized.includes("cam")) {
    return "📷";
  }
  if (normalized.includes("audio")) {
    return "🎧";
  }
  if (normalized.includes("software") || normalized.includes("sistema")) {
    return "💾";
  }
  if (normalized.includes("agua") || normalized.includes("líquido")) {
    return "💧";
  }
  return "🛠️";
};

export type { RepairVisual };
export {
  VISUAL_STORAGE_KEY,
  repairStatusLabels,
  repairStatusOptions,
  initialRepairForm,
  resolveDamageIcon,
};
