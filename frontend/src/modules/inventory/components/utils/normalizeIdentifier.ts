import type {
  InventoryCountLineInput,
  InventoryReceivingLineInput,
} from "@api/inventory";

type IdentifierLine = Pick<InventoryReceivingLineInput, "imei" | "serial"> &
  Pick<InventoryCountLineInput, "imei" | "serial">;

const digitsOnly = /^\d+$/u;

function normalizeIdentifier(identifier: string): IdentifierLine {
  const trimmed = identifier.trim();
  if (!trimmed) {
    return {};
  }
  if (digitsOnly.test(trimmed) && trimmed.length >= 8) {
    return { imei: trimmed };
  }
  return { serial: trimmed };
}

export default normalizeIdentifier;
