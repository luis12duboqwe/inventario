import { createContext, useContext } from "react";

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
} from "../../../../api";
import type { ModuleStatus } from "../../../../shared/components/ModuleHeader";
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

export type InventoryLayoutContextValue = {
  module: InventoryModuleState;
  smartImport: SmartImportManagerState;
  search: {
    inventoryQuery: string;
    setInventoryQuery: (value: string) => void;
    estadoFilter: Device["estado_comercial"] | "TODOS";
    setEstadoFilter: (value: Device["estado_comercial"] | "TODOS") => void;
    filteredDevices: Device[];
    highlightedDeviceIds: Set<number>;
  };
  editing: {
    editingDevice: Device | null;
    openEditDialog: (device: Device) => void;
    closeEditDialog: () => void;
    isEditDialogOpen: boolean;
    handleSubmitDeviceUpdates: (updates: DeviceUpdateInput, reason: string) => Promise<void>;
  };
  metrics: {
    statusCards: StatusCard[];
    storeValuationSnapshot: InventoryModuleState["storeValuationSnapshot"];
    lastBackup: InventoryModuleState["backupHistory"][number] | null;
    lastRefreshDisplay: string;
    totalCategoryUnits: number;
    categoryChartData: Array<{ label: string; value: number }>;
    moduleStatus: ModuleStatus;
    moduleStatusLabel: string;
    lowStockStats: { critical: number; warning: number };
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
    storeName: string | null;
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
    create: (
      input: Omit<InventoryReservationInput, "store_id">,
      reason: string,
    ) => Promise<void>;
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
    create: (
      deviceId: number,
      payload: ProductVariantCreateInput,
      reason: string,
    ) => Promise<void>;
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
    create: (
      payload: ProductBundleCreateInput,
      reason: string,
    ) => Promise<void>;
    update: (
      bundleId: number,
      payload: ProductBundleUpdateInput,
      reason: string,
    ) => Promise<void>;
    archive: (bundleId: number, reason: string) => Promise<void>;
  };
};

const InventoryLayoutContext = createContext<InventoryLayoutContextValue | undefined>(undefined);

export function useInventoryLayout(): InventoryLayoutContextValue {
  const context = useContext(InventoryLayoutContext);
  if (!context) {
    throw new Error("useInventoryLayout debe utilizarse dentro de InventoryLayoutContext.Provider");
  }
  return context;
}

export default InventoryLayoutContext;
