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
  const normalizedStoreId = storeId ?? fallbackStoreId ?? null;
  const normalizedStoreName = storeName ?? fallbackStoreName ?? null;
  const normalizedDeviceId =
    deviceId !== undefined && deviceId !== null ? deviceId : fallbackDeviceId ?? null;
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
