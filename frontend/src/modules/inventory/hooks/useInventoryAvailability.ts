import { useState, useCallback } from "react";
import { Device, getInventoryAvailability, InventoryAvailabilityRecord } from "@api/inventory";

export const buildAvailabilityReference = (device: Device): string => {
  const normalizedSku = device.sku?.trim().toLowerCase();
  if (normalizedSku) {
    return normalizedSku;
  }
  return `device:${device.id}`;
};

export function useInventoryAvailability(token: string) {
  const [availabilityRecords, setAvailabilityRecords] = useState<
    Record<string, InventoryAvailabilityRecord>
  >({});
  const [availabilityTarget, setAvailabilityTarget] = useState<Device | null>(null);
  const [availabilityOpen, setAvailabilityOpen] = useState(false);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [availabilityError, setAvailabilityError] = useState<string | null>(null);

  const handleCloseAvailability = useCallback(() => {
    setAvailabilityOpen(false);
    setAvailabilityError(null);
  }, []);

  const handleOpenAvailability = useCallback(
    async (device: Device) => {
      const reference = buildAvailabilityReference(device);
      setAvailabilityTarget(device);
      setAvailabilityOpen(true);
      setAvailabilityError(null);
      if (availabilityRecords[reference]) {
        return;
      }
      setAvailabilityLoading(true);
      try {
        const response = await getInventoryAvailability(token, {
          ...(device.sku ? { skus: [device.sku] } : {}),
          ...(device.sku ? {} : { deviceIds: [device.id] }),
          limit: 10,
        });
        const mapped: Record<string, InventoryAvailabilityRecord> = {};
        response.items.forEach((item) => {
          mapped[item.reference] = item;
        });
        setAvailabilityRecords((prev) => ({ ...prev, ...mapped }));
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "No fue posible consultar la disponibilidad corporativa.";
        setAvailabilityError(message);
      } finally {
        setAvailabilityLoading(false);
      }
    },
    [availabilityRecords, token],
  );

  return {
    availabilityRecords,
    availabilityTarget,
    availabilityOpen,
    availabilityLoading,
    availabilityError,
    handleOpenAvailability,
    handleCloseAvailability,
  };
}
