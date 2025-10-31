export function promptCorporateReason(defaultReason: string): string | null {
  const value = window.prompt(
    "Ingresa el motivo corporativo (X-Reason ≥ 5 caracteres)",
    defaultReason,
  );
  if (value === null) {
    return null;
  }
  return value.trim();
}
