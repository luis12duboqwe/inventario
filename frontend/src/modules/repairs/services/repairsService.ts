import {
  appendRepairOrderParts,
  closeRepairOrder,
  createRepairOrder,
  removeRepairOrderPart,
} from "../../../api"; // [PACK37-frontend]
import type {
  RepairOrderClosePayload,
  RepairOrderInput,
  RepairOrderPartsPayload,
} from "../../../api"; // [PACK37-frontend]

export const repairsService = {
  createRepairOrder: (token: string, payload: RepairOrderInput, reason: string) =>
    createRepairOrder(token, payload, reason), // [PACK37-frontend]
  appendParts: (token: string, repairId: number, payload: RepairOrderPartsPayload, reason: string) =>
    appendRepairOrderParts(token, repairId, payload, reason), // [PACK37-frontend]
  removePart: (token: string, repairId: number, partId: number, reason: string) =>
    removeRepairOrderPart(token, repairId, partId, reason), // [PACK37-frontend]
  closeRepair: (token: string, repairId: number, payload: RepairOrderClosePayload | undefined, reason: string) =>
    closeRepairOrder(token, repairId, payload, reason), // [PACK37-frontend]
};
