import { useMemo } from "react";

export function useInventoryStatus(
  lowStockDevices: number,
  totalDevices: number,
  reservationsMeta: { active_count: number } | undefined
) {
  return useMemo(() => {
    if (lowStockDevices > 0) return { status: "warning" as const, label: "Stock bajo" };
    if ((reservationsMeta?.active_count || 0) > 0) return { status: "ok" as const, label: "Reservas activas" };
    if (totalDevices === 0) return { status: "ok" as const, label: "Sin inventario" };
    return { status: "ok" as const, label: "Operativo" };
  }, [lowStockDevices, totalDevices, reservationsMeta]);
}
