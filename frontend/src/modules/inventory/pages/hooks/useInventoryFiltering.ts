import { useState, useMemo } from "react";
import { useLocation } from "react-router-dom";
import type { Device } from "@api/inventory";
import { useDashboard } from "../../../dashboard/context/DashboardContext";

export function useInventoryFiltering(
  devices: Device[],
  lowStockDevices: Array<{ device_id: number; quantity: number }>,
  selectedStoreId: number | null
) {
  const location = useLocation();
  const { globalSearchTerm, setGlobalSearchTerm } = useDashboard();

  const [inventoryQuery, setInventoryQuery] = useState("");
  const [estadoFilter, setEstadoFilter] = useState<Device["estado_comercial"] | "TODOS">("TODOS");

  // Track previous values to reset state on change during render
  const [prevPath, setPrevPath] = useState(location.pathname);
  const [prevStore, setPrevStore] = useState(selectedStoreId);
  const [prevGlobalSearch, setPrevGlobalSearch] = useState(globalSearchTerm);

  if (location.pathname !== prevPath || selectedStoreId !== prevStore) {
    setPrevPath(location.pathname);
    setPrevStore(selectedStoreId);
    setInventoryQuery("");
    setEstadoFilter("TODOS");
    if (location.pathname.startsWith("/dashboard/inventory")) {
      setGlobalSearchTerm("");
    }
  }

  if (globalSearchTerm !== prevGlobalSearch) {
    setPrevGlobalSearch(globalSearchTerm);
    if (location.pathname.startsWith("/dashboard/inventory")) {
      setInventoryQuery(globalSearchTerm);
    }
  }

  const filteredDevices = useMemo(() => {
    const normalizedQuery = inventoryQuery.trim().toLowerCase();
    return devices.filter((device) => {
      if (estadoFilter !== "TODOS" && device.estado_comercial !== estadoFilter) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      const haystack: Array<string | null | undefined> = [
        device.sku,
        device.name,
        device.imei,
        device.serial,
        device.modelo,
        device.marca,
        device.color,
        device.estado_comercial,
        device.categoria,
        device.condicion,
        device.estado,
        device.ubicacion,
        device.descripcion,
        device.proveedor,
        device.capacidad,
      ];
      return haystack.some((value) => {
        if (!value) {
          return false;
        }
        return value.toLowerCase().includes(normalizedQuery);
      });
    });
  }, [devices, estadoFilter, inventoryQuery]);

  const highlightedDevices = useMemo(
    () => new Set(lowStockDevices.map((entry) => entry.device_id)),
    [lowStockDevices]
  );

  return {
    inventoryQuery,
    setInventoryQuery,
    estadoFilter,
    setEstadoFilter,
    filteredDevices,
    highlightedDevices,
  };
}
