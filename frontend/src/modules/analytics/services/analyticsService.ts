import { getInventoryMetrics } from "@api/inventory";
import { getSummary } from "@api/stores";
import {
  getRotationAnalytics,
  getAgingAnalytics,
  getForecastAnalytics,
  getComparativeAnalytics,
  getProfitMarginAnalytics,
  getSalesProjectionAnalytics,
} from "@api/analytics";

export const analyticsService = {
  getInventoryMetrics,
  getSummary,
  getRotationAnalytics,
  getAgingAnalytics,
  getForecastAnalytics,
  getComparativeAnalytics,
  getProfitMarginAnalytics,
  getSalesProjectionAnalytics,
};
