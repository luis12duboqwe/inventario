import React from "react";

import LabelGenerator from "./LabelGenerator";

type LabelPrinterProps = {
  open?: boolean;
  onClose?: () => void;
  storeId?: number | null;
  storeName?: string | null;
  deviceId?: string | number | null;
  deviceName?: string | null;
  sku?: string | null;
  fallbackStoreId?: number | null;
  fallbackStoreName?: string | null;
  fallbackDeviceId?: string | number | null;
  fallbackDeviceName?: string | null;
  fallbackSku?: string | null;
};

export default function LabelPrinter({
  open,
  onClose,
  storeId,
  storeName,
  deviceId,
  deviceName,
  sku,
  fallbackStoreId,
  fallbackStoreName,
  fallbackDeviceId,
  fallbackDeviceName,
  fallbackSku,
}: LabelPrinterProps) {
  const normalizeId = (value: string | number | null | undefined) => {
    if (value === undefined || value === null) return null;
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  };

  const normalizedStoreId = normalizeId(storeId ?? fallbackStoreId);
  const normalizedStoreName = storeName ?? fallbackStoreName ?? null;
  const normalizedDeviceId = normalizeId(deviceId ?? fallbackDeviceId);
  const normalizedDeviceName = deviceName ?? fallbackDeviceName ?? null;
  const normalizedSku = sku ?? fallbackSku ?? null;

  return (
    <LabelGenerator
      open={open}
      onClose={onClose}
      storeId={normalizedStoreId as number | null}
      storeName={normalizedStoreName}
      deviceId={normalizedDeviceId as string | number | null}
      deviceName={normalizedDeviceName}
      sku={normalizedSku}
    />
  );
}
