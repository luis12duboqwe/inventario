const HN_LOCALE = "es-HN";

function getUsdRate(): number {
  const raw = import.meta.env.VITE_USD_RATE ?? "24.5";
  const parsed = Number.parseFloat(String(raw));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 24.5;
}

export function formatDateTimeHn(value: Date | string | number): string {
  const date = typeof value === "string" || typeof value === "number" ? new Date(value) : value;
  return new Intl.DateTimeFormat(HN_LOCALE, { dateStyle: "short", timeStyle: "short" }).format(date);
}

export function formatDateHn(value: Date | string | number): string {
  const date = typeof value === "string" || typeof value === "number" ? new Date(value) : value;
  return new Intl.DateTimeFormat(HN_LOCALE, { dateStyle: "short" }).format(date);
}

export function formatNumberHn(value: number, options?: Intl.NumberFormatOptions): string {
  return new Intl.NumberFormat(HN_LOCALE, options).format(value);
}

export function formatCurrencyHnl(value: number): string {
  return new Intl.NumberFormat(HN_LOCALE, {
    style: "currency",
    currency: "HNL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatCurrencyUsd(value: number): string {
  return new Intl.NumberFormat(HN_LOCALE, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatCurrencyWithUsd(value: number, usdRate = getUsdRate()): string {
  const local = formatCurrencyHnl(value);
  if (!usdRate || !Number.isFinite(usdRate) || usdRate <= 0) {
    return local;
  }
  const usdValue = value / usdRate;
  return `${local} (≈ ${formatCurrencyUsd(usdValue)})`;
}

export function formatPercentHn(value: number): string {
  return `${formatNumberHn(value, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} %`;
}
