const coerceFlag = (value: string | boolean | undefined, defaultValue: boolean): boolean => {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (normalized === "0" || normalized === "false" || normalized === "off") {
      return false;
    }
    if (normalized === "1" || normalized === "true" || normalized === "on") {
      return true;
    }
  }
  return defaultValue;
};

export const featureFlags = {
  catalogPro: coerceFlag(import.meta.env.VITE_SOFTMOBILE_ENABLE_CATALOG_PRO, true),
  transfers: coerceFlag(import.meta.env.VITE_SOFTMOBILE_ENABLE_TRANSFERS, true),
  purchasesSales: coerceFlag(import.meta.env.VITE_SOFTMOBILE_ENABLE_PURCHASES_SALES, true),
  analyticsAdv: coerceFlag(import.meta.env.VITE_SOFTMOBILE_ENABLE_ANALYTICS_ADV, true),
  twoFactor: coerceFlag(import.meta.env.VITE_SOFTMOBILE_ENABLE_2FA, false),
  hybridPrep: coerceFlag(import.meta.env.VITE_SOFTMOBILE_ENABLE_HYBRID_PREP, true),
  priceLists: coerceFlag(import.meta.env.VITE_SOFTMOBILE_ENABLE_PRICE_LISTS, false),
  bundles: coerceFlag(import.meta.env.VITE_SOFTMOBILE_ENABLE_BUNDLES, false),
  dte: coerceFlag(import.meta.env.VITE_SOFTMOBILE_ENABLE_DTE, false),
} as const;

export type FeatureFlagKey = keyof typeof featureFlags;

export const isFeatureEnabled = (flag: FeatureFlagKey): boolean => featureFlags[flag];
