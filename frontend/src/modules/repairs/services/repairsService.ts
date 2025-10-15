import { createRepairOrder } from "../../../api";
import type { RepairOrderInput } from "../../../api";

export const repairsService = {
  createRepairOrder: (token: string, payload: RepairOrderInput) => createRepairOrder(token, payload),
};
