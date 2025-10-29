import type { Customer, Device, Store } from "../api";

type RepairPartForm = {
  deviceId: number | null;
  quantity: number;
  unitCost: number;
};

type RepairForm = {
  storeId: number | null;
  customerId: number | null;
  customerName: string;
  technicianName: string;
  damageType: string;
  deviceDescription: string;
  notes: string;
  laborCost: number;
  parts: RepairPartForm[];
};

export type { Customer, Device, Store, RepairForm, RepairPartForm };
