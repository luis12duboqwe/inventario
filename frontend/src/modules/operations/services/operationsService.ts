import {
  createPurchaseOrder,
  receivePurchaseOrder,
  registerPurchaseReturn,
} from "@api/purchases";
import {
  createSale,
  registerSaleReturn,
} from "@api/sales";
import {
  createTransferOrder,
  dispatchTransferOrder,
  receiveTransferOrder,
} from "@api/transfers";

export const operationsService = {
  createPurchaseOrder,
  receivePurchaseOrder,
  registerPurchaseReturn,
  createSale,
  registerSaleReturn,
  createTransferOrder,
  dispatchTransferOrder,
  receiveTransferOrder,
};
