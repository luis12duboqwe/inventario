import type { Sale } from "../../../../api";

export const TAX_RATE = 0.16;

export const PAYMENT_LABELS: Record<Sale["payment_method"], string> = {
  EFECTIVO: "Efectivo",
  TARJETA: "Tarjeta",
  TRANSFERENCIA: "Transferencia",
  CREDITO: "Crédito",
  OTRO: "Otro",
  NOTA_CREDITO: "Nota de Crédito",
};
