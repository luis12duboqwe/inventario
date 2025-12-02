import { useState, useMemo, type FormEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useOperationsModule } from "../../hooks/useOperationsModule";
import { useDashboard } from "../../../dashboard/context/DashboardContext";
import { useDebounce } from "../../../../hooks/useDebounce";
import { listCustomers } from "@api/customers";
import { getDevices } from "@api/inventory";
import { createSale, listSales } from "@api/sales";
import type { Device } from "@api/inventory";
import type { SaleCreateInput } from "@api/sales";
import type { SaleLine, SaleFormState, SalesFilterState, SaleSummary } from "./types";
import { TAX_RATE, PAYMENT_LABELS } from "./constants";

const initialSaleForm: SaleFormState = {
  storeId: null,
  paymentMethod: "EFECTIVO",
  discountPercent: 0,
  customerId: null,
  customerName: "",
  notes: "",
  reason: "",
};

const initialFilters: SalesFilterState = {
  storeId: null,
  customerId: null,
  userId: null,
  dateFrom: new Date().toISOString().split("T")[0] as string,
  dateTo: new Date().toISOString().split("T")[0] as string,
  query: "",
};

export function useSalesLogic() {
  const { token, stores, selectedStoreId } = useOperationsModule();
  const { pushToast } = useDashboard();
  const queryClient = useQueryClient();

  // State
  const [saleForm, setSaleForm] = useState<SaleFormState>({
    ...initialSaleForm,
    storeId: selectedStoreId
  });
  const [deviceQuery, setDeviceQuery] = useState("");
  const debouncedDeviceQuery = useDebounce(deviceQuery, 300);
  const [saleItems, setSaleItems] = useState<SaleLine[]>([]);
  const [salesFilters, setSalesFilters] = useState<SalesFilterState>(initialFilters);
  const [invoiceAvailable, setInvoiceAvailable] = useState(false);
  const [isPrinting, setIsPrinting] = useState(false);

  // Queries
  const { data: customers = [] } = useQuery({
    queryKey: ["customers"],
    queryFn: () => listCustomers(token),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  const { data: devices = [], isLoading: isLoadingDevices } = useQuery({
    queryKey: ["devices", saleForm.storeId, debouncedDeviceQuery],
    queryFn: () => {
      if (!saleForm.storeId) return Promise.resolve([]);
      return getDevices(token, saleForm.storeId, {
        search: debouncedDeviceQuery,
        limit: 20
      });
    },
    enabled: !!saleForm.storeId,
  });

  const { data: sales = [], isLoading: isLoadingSales } = useQuery({
    queryKey: ["sales", salesFilters],
    queryFn: () => listSales(token, {
      storeId: salesFilters.storeId,
      customerId: salesFilters.customerId,
      userId: salesFilters.userId,
      dateFrom: salesFilters.dateFrom,
      dateTo: salesFilters.dateTo,
      query: salesFilters.query,
    }),
  });

  // Mutations
  const createSaleMutation = useMutation({
    mutationFn: async (payload: SaleCreateInput) => {
      return createSale(token, payload, saleForm.reason || "Venta mostrador");
    },
    onSuccess: () => {
      pushToast({ message: "Venta registrada exitosamente", variant: "success" });
      handleReset();
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      setInvoiceAvailable(true);
    },
    onError: (error) => {
      console.error("Error creating sale:", error);
      pushToast({
        message: error instanceof Error ? error.message : "Error al registrar venta",
        variant: "error"
      });
    }
  });

  // Handlers
  const handleSaleFormChange = (updates: Partial<SaleFormState>) => {
    setSaleForm(prev => ({ ...prev, ...updates }));
  };

  const handleAddDevice = (device: Device) => {
    setSaleItems(prev => {
      const existing = prev.find(item => item.device.id === device.id);
      if (existing) {
        return prev.map(item =>
          item.device.id === device.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }
      return [...prev, { device, quantity: 1, batchCode: "" }];
    });
    setDeviceQuery(""); // Clear search after adding
  };

  const handleQuantityChange = (deviceId: number, qty: number) => {
    setSaleItems(prev => prev.map((item) =>
      item.device.id === deviceId ? { ...item, quantity: Math.max(1, qty) } : item
    ));
  };

  const handleBatchCodeChange = (deviceId: number, code: string) => {
    setSaleItems(prev => prev.map((item) =>
      item.device.id === deviceId ? { ...item, batchCode: code } : item
    ));
  };

  const handleRemoveLine = (deviceId: number) => {
    setSaleItems(prev => prev.filter((item) => item.device.id !== deviceId));
  };

  const handleSalesFiltersChange = (updates: Partial<SalesFilterState>) => {
    setSalesFilters(prev => ({ ...prev, ...updates }));
  };

  const handleReset = () => {
    setSaleForm({ ...initialSaleForm, storeId: selectedStoreId });
    setSaleItems([]);
    setDeviceQuery("");
    setInvoiceAvailable(false);
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!saleForm.storeId || saleItems.length === 0) return;

    const payload: SaleCreateInput = {
      store_id: saleForm.storeId,
      ...(saleForm.customerId ? { customer_id: saleForm.customerId } : {}),
      payment_method: saleForm.paymentMethod,
      discount_percent: saleForm.discountPercent,
      notes: saleForm.notes,
      items: saleItems.map(item => ({
        device_id: item.device.id,
        quantity: item.quantity,
        batch_code: item.batchCode || null,
      })),
    };

    createSaleMutation.mutate(payload);
  };

  const handleRequestInvoice = async () => {
    setIsPrinting(true);
    try {
      // Logic to request invoice for the last sale or selected sale
      // For now, just a placeholder
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate delay
      pushToast({ message: "Solicitud de factura enviada", variant: "info" });
    } catch (error) {
      pushToast({ message: "Error al solicitar factura", variant: "error" });
    } finally {
      setIsPrinting(false);
    }
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" }).format(val);
  };

  // Calculations
  const saleSummary = useMemo<SaleSummary>(() => {
    const gross = saleItems.reduce((sum, item) => {
      const price = Number(item.device.precio_venta || 0);
      return sum + (price * item.quantity);
    }, 0);

    const discount = gross * (saleForm.discountPercent / 100);
    const subtotal = gross - discount;
    const taxAmount = subtotal * TAX_RATE;
    const total = subtotal + taxAmount;

    return {
      gross,
      discount,
      subtotal,
      taxAmount,
      total,
      taxRate: TAX_RATE,
    };
  }, [saleItems, saleForm.discountPercent]);

  return {
    stores,
    customers,
    saleForm,
    handleSaleFormChange,
    deviceQuery,
    setDeviceQuery,
    devices,
    isLoadingDevices,
    handleAddDevice,
    saleItems,
    handleQuantityChange,
    handleBatchCodeChange,
    handleRemoveLine,
    saleSummary,
    paymentLabels: PAYMENT_LABELS,
    isSaving: createSaleMutation.isPending,
    isPrinting,
    handleSubmit,
    handleReset,
    handleRequestInvoice,
    formatCurrency,
    invoiceAvailable,
    sales,
    isLoadingSales,
    salesFilters,
    handleSalesFiltersChange,
  };
}
