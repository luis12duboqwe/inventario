// [PACK36-safe-utils]
export function safeArray<T>(value: T[] | null | undefined): T[] {
  if (Array.isArray(value)) {
    return value;
  }
  return [];
}

// [PACK36-safe-utils]
export function safeNumber(value: unknown, defaultValue = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return defaultValue;
}

// [PACK36-safe-utils]
export function safeDate(value: unknown, fallback: Date | null = null): Date | null {
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return value;
  }
  if (typeof value === "number") {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? fallback : date;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? fallback : date;
  }
  return fallback;
}

// [PACK36-safe-utils]
export function safeString(value: unknown, defaultValue = ""): string {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number") {
    return String(value);
  }
  return defaultValue;
}
