import { useState } from "react";
import type { Device, DeviceUpdateInput } from "@api/inventory";
import { inventoryService } from "../../services/inventoryService";

export function useInventoryEdit(
  token: string,
  selectedStoreId: number | null,
  refreshSummary: () => Promise<void>,
  pushToast: (msg: string, type: "success" | "error") => void,
  setError: (err: string | null) => void
) {
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);

  const openEditDialog = (device: Device) => {
    setEditingDevice(device);
    setIsEditDialogOpen(true);
  };

  const closeEditDialog = () => {
    setEditingDevice(null);
    setIsEditDialogOpen(false);
  };

  const handleSubmitDeviceUpdates = async (updates: DeviceUpdateInput, reason: string) => {
    if (!editingDevice || !selectedStoreId) return;
    try {
      await inventoryService.updateDevice(token, selectedStoreId, editingDevice.id, updates, reason);
      pushToast("Dispositivo actualizado correctamente", "success");
      closeEditDialog();
      await refreshSummary();
    } catch (err) {
      console.error(err);
      setError("Error al actualizar dispositivo");
    }
  };

  return {
    editingDevice,
    isEditDialogOpen,
    openEditDialog,
    closeEditDialog,
    handleSubmitDeviceUpdates,
  };
}
