import { rememberReason } from "./reasonStorage";

export function promptCorporateReason(defaultReason: string): string | null {
  const value = window.prompt(
    "Ingresa el motivo corporativo (X-Reason ≥ 5 caracteres)",
    defaultReason,
  );
  if (value === null) {
    return null;
  }
  const trimmed = value.trim();
  if (trimmed.length >= 5) {
    rememberReason(trimmed);
  }
  return trimmed;
}
