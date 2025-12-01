import {
  appendRepairOrderParts,
  closeRepairOrder,
  createRepairOrder,
  removeRepairOrderPart,
} from "@api/repairs";
import type {
  RepairOrderClosePayload,
  RepairOrderPayload,
  RepairOrderPartsPayload,
} from "@api/repairs";

export const repairsService = {
  createRepairOrder: (token: string, payload: RepairOrderPayload, reason: string) =>
    createRepairOrder(token, payload, reason),
  appendParts: (token: string, repairId: number, payload: RepairOrderPartsPayload, reason: string) =>
    appendRepairOrderParts(token, repairId, payload, reason),
  removePart: (token: string, repairId: number, partId: number, reason: string) =>
    removeRepairOrderPart(token, repairId, partId, reason),
  closeRepair: (token: string, repairId: number, payload: RepairOrderClosePayload | undefined, reason: string) =>
    closeRepairOrder(token, repairId, payload, reason),
};
