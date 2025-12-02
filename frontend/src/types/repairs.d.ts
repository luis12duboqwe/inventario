import type { Customer } from "@api/customers";
import type { Device } from "@api/inventory";
import type { Store } from "@api/stores";

type RepairPartForm = {
  deviceId: number | null;
  quantity: number;
  unitCost: number;
  source: "STOCK" | "EXTERNAL"; // [PACK37-frontend]
  partName: string;
};

type RepairForm = {
  storeId: number | null;
  customerId: number | null;
  customerName: string;
  customerContact: string;
  technicianName: string;
  damageType: string;
  diagnosis: string;
  deviceModel: string;
  imei: string;
  deviceDescription: string;
  problemDescription: string;
  notes: string;
  estimatedCost: number;
  depositAmount: number;
  laborCost: number;
  parts: RepairPartForm[];
};

export type { Customer, Device, Store, RepairForm, RepairPartForm };
