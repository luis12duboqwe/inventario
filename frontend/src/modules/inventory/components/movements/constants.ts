import type { MovementInput } from "../../../../api";

export type MovementType = MovementInput["tipo_movimiento"];
export type MovementFilterType = MovementType | "ALL";

export const MOVEMENT_TYPE_LABELS: Record<MovementType, string> = {
  entrada: "Entrada",
  salida: "Salida",
  ajuste: "Ajuste",
};

export const MOVEMENT_TYPE_PLURAL_LABELS: Record<MovementType, string> = {
  entrada: "Entradas",
  salida: "Salidas",
  ajuste: "Ajustes",
};

export const MOVEMENT_TYPE_OPTIONS: Array<{ value: MovementType; label: string }> = [
  { value: "entrada", label: MOVEMENT_TYPE_LABELS.entrada },
  { value: "salida", label: MOVEMENT_TYPE_LABELS.salida },
  { value: "ajuste", label: MOVEMENT_TYPE_LABELS.ajuste },
];

export const MOVEMENT_FILTER_OPTIONS: Array<{ value: MovementFilterType; label: string }> = [
  { value: "ALL", label: "Todos" },
  ...MOVEMENT_TYPE_OPTIONS,
];

export function getMovementTypeLabel(type: MovementType): string {
  return MOVEMENT_TYPE_LABELS[type] ?? type;
}

export function getMovementTypePluralLabel(type: MovementType): string {
  return MOVEMENT_TYPE_PLURAL_LABELS[type] ?? type;
}
