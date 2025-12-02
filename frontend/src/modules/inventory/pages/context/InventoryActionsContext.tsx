import React, { createContext, useContext } from "react";
import type {
  Device,
  DeviceImportSummary,
  DeviceUpdateInput,
  InventoryReservation,
  InventoryReservationInput,
  InventoryReservationRenewInput,
  ProductVariant,
  ProductVariantCreateInput,
  ProductVariantUpdateInput,
  ProductBundle,
  ProductBundleCreateInput,
  ProductBundleUpdateInput,
} from "@api/inventory";
import type { InventoryModuleState, SmartImportManagerState } from "./types";

export type InventoryActionsContextValue = {
  module: InventoryModuleState;
  smartImport: SmartImportManagerState;
  editing: {
    editingDevice: Device | null;
    openEditDialog: (device: Device) => void;
    closeEditDialog: () => void;
    isEditDialogOpen: boolean;
    handleSubmitDeviceUpdates: (updates: DeviceUpdateInput, reason: string) => Promise<void>;
  };
  downloads: {
    triggerRefreshSummary: () => void;
    triggerDownloadReport: () => void;
    triggerDownloadCsv: () => void;
    triggerExportCatalog: () => void;
    triggerImportCatalog: () => void;
    downloadSmartResultCsv: () => void;
    downloadSmartResultPdf: () => void;
    triggerRefreshSupplierOverview: () => void;
    triggerRefreshRecentMovements: () => void;
  };
  catalog: {
    catalogFile: File | null;
    setCatalogFile: (file: File | null) => void;
    importingCatalog: boolean;
    exportingCatalog: boolean;
    lastImportSummary: DeviceImportSummary | null;
    fileInputRef: React.RefObject<HTMLInputElement>;
  };
  alerts: {
    thresholdDraft: number;
    setThresholdDraft: (value: number) => void;
    updateThresholdDraftValue: (value: number) => void;
    handleSaveThreshold: () => Promise<void>;
    isSavingThreshold: boolean;
  };
  helpers: {
    storeNameById: Map<number, string>;
    resolvePendingFields: (device: Device) => string[];
    resolveLowStockSeverity: (quantity: number) => "critical" | "warning" | "notice";
  };
  labeling: {
    open: boolean;
    device: Device | null;
    storeId: number | null;
    storeName: string | undefined;
    openLabelPrinter: (device: Device) => void;
    closeLabelPrinter: () => void;
  };
  reservations: {
    items: InventoryReservation[];
    meta: { page: number; size: number; total: number; pages: number };
    loading: boolean;
    includeExpired: boolean;
    setIncludeExpired: (value: boolean) => void;
    refresh: (page?: number) => Promise<void>;
    create: (input: Omit<InventoryReservationInput, "store_id">, reason: string) => Promise<void>;
    renew: (
      reservationId: number,
      input: InventoryReservationRenewInput,
      reason: string,
    ) => Promise<void>;
    cancel: (reservationId: number, reason: string) => Promise<void>;
    expiringSoon: InventoryReservation[];
  };
  variants: {
    enabled: boolean;
    loading: boolean;
    includeInactive: boolean;
    setIncludeInactive: (value: boolean) => void;
    items: ProductVariant[];
    refresh: () => Promise<void>;
    create: (deviceId: number, payload: ProductVariantCreateInput, reason: string) => Promise<void>;
    update: (
      variantId: number,
      payload: ProductVariantUpdateInput,
      reason: string,
    ) => Promise<void>;
    archive: (variantId: number, reason: string) => Promise<void>;
  };
  bundles: {
    enabled: boolean;
    loading: boolean;
    includeInactive: boolean;
    setIncludeInactive: (value: boolean) => void;
    items: ProductBundle[];
    refresh: () => Promise<void>;
    create: (payload: ProductBundleCreateInput, reason: string) => Promise<void>;
    update: (bundleId: number, payload: ProductBundleUpdateInput, reason: string) => Promise<void>;
    archive: (bundleId: number, reason: string) => Promise<void>;
  };
};

export const InventoryActionsContext = createContext<InventoryActionsContextValue | undefined>(
  undefined,
);

export function useInventoryActions(): InventoryActionsContextValue {
  const context = useContext(InventoryActionsContext);
  if (!context) {
    throw new Error("useInventoryActions must be used within InventoryActionsContext.Provider");
  }
  return context;
}
