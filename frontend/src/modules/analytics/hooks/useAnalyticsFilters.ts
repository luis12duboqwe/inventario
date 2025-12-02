import { useMemo, useState, useEffect } from "react";
import type { AnalyticsFilters } from "@api/analytics";
import { getAnalyticsCategories } from "@api/analytics";
import { listPurchaseVendors } from "@api/purchases";

type UseAnalyticsFiltersParams = {
  token: string;
  pushToast: (toast: { message: string; variant: "success" | "error" | "info" | "warning" }) => void;
};

export function useAnalyticsFilters({ token, pushToast }: UseAnalyticsFiltersParams) {
  const [selectedStore, setSelectedStore] = useState<number | "all">("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedSupplier, setSelectedSupplier] = useState<string>("all");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  const [categories, setCategories] = useState<string[]>([]);
  const [suppliers, setSuppliers] = useState<string[]>([]);

  const storeIds = useMemo(
    () => (selectedStore === "all" ? undefined : [selectedStore]),
    [selectedStore],
  );

  const analyticsFilters = useMemo<AnalyticsFilters>(() => {
    const filters: AnalyticsFilters = {};
    if (storeIds && storeIds.length > 0) {
      filters.storeIds = storeIds;
    }
    if (dateFrom) {
      filters.dateFrom = dateFrom;
    }
    if (dateTo) {
      filters.dateTo = dateTo;
    }
    if (selectedCategory !== "all") {
      filters.category = selectedCategory;
    }
    if (selectedSupplier !== "all") {
      filters.supplier = selectedSupplier;
    }
    return filters;
  }, [dateFrom, dateTo, selectedCategory, selectedSupplier, storeIds]);

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await getAnalyticsCategories(token);
        setCategories(response.categories);
      } catch (err) {
        const message =
          err instanceof Error
            ? `No fue posible cargar categorías: ${err.message}`
            : "No fue posible cargar categorías";
        pushToast({ message, variant: "error" });
      }
    };
    void fetchCategories();
  }, [pushToast, token]);

  if (
    selectedCategory !== "all" &&
    categories.length > 0 &&
    !categories.includes(selectedCategory)
  ) {
    setSelectedCategory("all");
  }

  useEffect(() => {
    const fetchSuppliers = async () => {
      try {
        const vendors = await listPurchaseVendors(token, { status: "activo", limit: 100 });
        const names = Array.from(
          new Set(
            vendors
              .map((vendor) => vendor.nombre?.trim())
              .filter((name): name is string => Boolean(name && name.length > 0)),
          ),
        ).sort((a, b) => a.localeCompare(b));
        setSuppliers(names);
      } catch (err) {
        const message =
          err instanceof Error
            ? `No fue posible cargar proveedores: ${err.message}`
            : "No fue posible cargar proveedores";
        pushToast({ message, variant: "error" });
      }
    };
    void fetchSuppliers();
  }, [pushToast, token]);

  if (
    selectedSupplier !== "all" &&
    suppliers.length > 0 &&
    !suppliers.includes(selectedSupplier)
  ) {
    setSelectedSupplier("all");
  }

  return {
    selectedStore,
    setSelectedStore,
    selectedCategory,
    setSelectedCategory,
    selectedSupplier,
    setSelectedSupplier,
    dateFrom,
    setDateFrom,
    dateTo,
    setDateTo,
    categories,
    suppliers,
    analyticsFilters,
  };
}
