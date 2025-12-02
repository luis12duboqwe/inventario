import { useState, useCallback } from "react";
import type { Device, CatalogDevice } from "@api/inventory";
import type { Store } from "@api/types";

export function useInventoryLabeling(
  selectedStore: Store | null,
  selectedStoreId: number | null,
  storeNameById: Map<number, string>
) {
  const [labelingDevice, setLabelingDevice] = useState<Device | null>(null);
  const [labelingStoreId, setLabelingStoreId] = useState<number | null>(null);
  const [labelingStoreName, setLabelingStoreName] = useState<string | null>(null);
  const [isLabelPrinterOpen, setIsLabelPrinterOpen] = useState(false);

  const openLabelPrinter = useCallback(
    (target: Device) => {
      const resolvedStoreId = target.store_id ?? selectedStoreId ?? null;
      setLabelingDevice(target);
      setLabelingStoreId(resolvedStoreId);
      const resolvedName =
        (resolvedStoreId != null ? storeNameById.get(resolvedStoreId) : null) ??
        ("store_name" in target ? (target as CatalogDevice).store_name : null) ??
        selectedStore?.name ??
        null;
      setLabelingStoreName(resolvedName);
      setIsLabelPrinterOpen(true);
    },
    [selectedStoreId, selectedStore, storeNameById]
  );

  const closeLabelPrinter = useCallback(() => {
    setIsLabelPrinterOpen(false);
    setLabelingDevice(null);
  }, []);

  return {
    labelingDevice,
    labelingStoreId,
    labelingStoreName,
    isLabelPrinterOpen,
    openLabelPrinter,
    closeLabelPrinter,
  };
}
