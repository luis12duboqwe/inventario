import { useCallback, useEffect, useMemo, useState } from "react";
import type { Store } from "@api/stores";
import type { UserAccount } from "@api/users";
import { listUsers } from "@api/users";
import { usePurchaseOrders } from "./purchases/hooks/usePurchaseOrders";
import { usePurchaseRecords } from "./purchases/hooks/usePurchaseRecords";
import { usePurchaseVendors } from "./purchases/hooks/usePurchaseVendors";
import { usePurchaseStatistics } from "./purchases/hooks/usePurchaseStatistics";
import { usePurchaseTemplates } from "./purchases/hooks/usePurchaseTemplates";
import { usePurchaseCsv } from "./purchases/hooks/usePurchaseCsv";

export type PurchasesControllerParams = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
  onInventoryRefresh?: () => void;
};

const useReasonPrompt = (setError: (message: string | null) => void) => {
  return (promptText: string) => {
    const reason = window.prompt(promptText, "");
    if (!reason || reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo (mínimo 5 caracteres).");
      return null;
    }
    return reason.trim();
  };
};

const useBlobDownloader = () => {
  return (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };
};

const paymentOptions = ["EFECTIVO", "TRANSFERENCIA", "TARJETA", "CREDITO", "OTRO"] as const;

export const usePurchasesController = ({
  token,
  stores,
  defaultStoreId = null,
  onInventoryRefresh,
}: PurchasesControllerParams) => {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);

  const askReason = useReasonPrompt(setError);
  const downloadBlob = useBlobDownloader();

  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" }),
    [],
  );

  const vendorsLogic = usePurchaseVendors({
    token,
    askReason,
    setError,
    setMessage,
    downloadBlob,
  });

  const statisticsLogic = usePurchaseStatistics({
    token,
    setError,
  });

  const recordsLogic = usePurchaseRecords({
    token,
    defaultStoreId,
    askReason,
    setError,
    setMessage,
    downloadBlob,
    loadStatistics: statisticsLogic.loadStatistics,
    loadVendors: vendorsLogic.loadVendors,
  });

  const ordersLogic = usePurchaseOrders({
    token,
    defaultStoreId,
    askReason,
    setError,
    setMessage,
    onInventoryRefresh: onInventoryRefresh ?? (() => { /* no-op */ }),
  });

  const templatesLogic = usePurchaseTemplates({
    token,
    form: ordersLogic.form,
    setForm: ordersLogic.setForm,
    refreshOrders: ordersLogic.refreshOrders,
    askReason,
    setError,
    setMessage,
    onInventoryRefresh: onInventoryRefresh ?? (() => { /* no-op */ }),
  });

  const csvLogic = usePurchaseCsv({
    token,
    form: ordersLogic.form,
    refreshOrders: ordersLogic.refreshOrders,
    loadRecurringOrders: templatesLogic.loadRecurringOrders,
    askReason,
    setError,
    setMessage,
    onInventoryRefresh: onInventoryRefresh ?? (() => { /* no-op */ }),
  });

  const loadUsers = useCallback(async () => {
    try {
      setUsersLoading(true);
      const data = await listUsers(token);
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cargar usuarios disponibles");
    } finally {
      setUsersLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  const selectedStore = useMemo(
    () => stores.find((store) => store.id === ordersLogic.form.storeId) ?? null,
    [stores, ordersLogic.form.storeId],
  );

  return {
    // Shared
    message,
    error,
    currencyFormatter,
    paymentOptions,
    selectedStore,
    users,
    usersLoading,

    // Orders
    orders: ordersLogic.orders,
    loading: ordersLogic.loading,
    form: ordersLogic.form,
    devices: ordersLogic.devices,
    updateForm: ordersLogic.updateForm,
    handleCreate: ordersLogic.handleCreate,
    handleReceive: ordersLogic.handleReceive,
    handleCancel: ordersLogic.handleCancel,

    // Records
    records: recordsLogic.records,
    recordsLoading: recordsLogic.recordsLoading,
    recordForm: recordsLogic.recordForm,
    recordItems: recordsLogic.recordItems,
    recordDevices: recordsLogic.recordDevices,
    recordStatusOptions: recordsLogic.recordStatusOptions,
    recordSubtotal: recordsLogic.recordSubtotal,
    recordTax: recordsLogic.recordTax,
    recordTotal: recordsLogic.recordTotal,
    recordFiltersDraft: recordsLogic.recordFiltersDraft,
    updateRecordForm: recordsLogic.updateRecordForm,
    updateRecordItem: recordsLogic.updateRecordItem,
    addRecordItem: recordsLogic.addRecordItem,
    removeRecordItem: recordsLogic.removeRecordItem,
    handleRecordSubmit: recordsLogic.handleRecordSubmit,
    handleRecordFiltersDraftChange: recordsLogic.handleRecordFiltersDraftChange,
    handleRecordFiltersSubmit: recordsLogic.handleRecordFiltersSubmit,
    handleRecordFiltersReset: recordsLogic.handleRecordFiltersReset,
    handleExportRecords: recordsLogic.handleExportRecords,

    // Vendors
    vendors: vendorsLogic.vendors,
    vendorsLoading: vendorsLogic.vendorsLoading,
    vendorForm: vendorsLogic.vendorForm,
    editingVendorId: vendorsLogic.editingVendorId,
    selectedVendor: vendorsLogic.selectedVendor,
    vendorHistory: vendorsLogic.vendorHistory,
    vendorHistoryLoading: vendorsLogic.vendorHistoryLoading,
    vendorSaving: vendorsLogic.vendorSaving,
    vendorExporting: vendorsLogic.vendorExporting,
    vendorFiltersDraft: vendorsLogic.vendorFiltersDraft,
    vendorHistoryFiltersDraft: vendorsLogic.vendorHistoryFiltersDraft,
    handleVendorFormSubmit: vendorsLogic.handleVendorFormSubmit,
    handleVendorInputChange: vendorsLogic.handleVendorInputChange,
    resetVendorForm: vendorsLogic.resetVendorForm,
    handleVendorEdit: vendorsLogic.handleVendorEdit,
    handleVendorStatusToggle: vendorsLogic.handleVendorStatusToggle,
    handleVendorExport: vendorsLogic.handleVendorExport,
    handleVendorFiltersSubmit: vendorsLogic.handleVendorFiltersSubmit,
    handleVendorFiltersReset: vendorsLogic.handleVendorFiltersReset,
    handleVendorHistoryFiltersSubmit: vendorsLogic.handleVendorHistoryFiltersSubmit,
    handleVendorHistoryFiltersReset: vendorsLogic.handleVendorHistoryFiltersReset,
    handleSelectVendor: vendorsLogic.handleSelectVendor,
    handleVendorFiltersDraftChange: vendorsLogic.handleVendorFiltersDraftChange,
    handleVendorHistoryFiltersDraftChange: vendorsLogic.handleVendorHistoryFiltersDraftChange,

    // Statistics
    statistics: statisticsLogic.statistics,
    statsLoading: statisticsLogic.statisticsLoading,

    // Templates
    recurringOrders: templatesLogic.recurringOrders,
    recurringLoading: templatesLogic.recurringLoading,
    templateName: templatesLogic.templateName,
    templateDescription: templatesLogic.templateDescription,
    templateSaving: templatesLogic.templateSaving,
    setTemplateName: templatesLogic.setTemplateName,
    setTemplateDescription: templatesLogic.setTemplateDescription,
    handleSaveTemplate: templatesLogic.handleSaveTemplate,
    handleApplyTemplate: templatesLogic.handleApplyTemplate,
    handleExecuteTemplate: templatesLogic.handleExecuteTemplate,
    getTemplateSupplier: templatesLogic.getTemplateSupplier,

    // CSV
    csvLoading: csvLogic.csvLoading,
    handleImportCsv: csvLogic.handleImportCsv,

    // Legacy aliases for compatibility if needed (none identified as critical missing)
    handleReturn: ordersLogic.handleReturn,
  } as const;
};

export type PurchasesControllerState = ReturnType<typeof usePurchasesController>;

export { paymentOptions };
