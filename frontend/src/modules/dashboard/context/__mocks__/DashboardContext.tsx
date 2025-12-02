import type { ReactNode } from "react";
import { vi } from "vitest";
import type { DashboardContextValue } from "../DashboardContext";

const dashboardContextValue = {
  enablePriceLists: true,
  refreshObservability: vi.fn(),
} as unknown as DashboardContextValue;

export const DashboardProvider = ({ children }: { children: ReactNode }) => (
  <div data-testid="dashboard-provider-mock">{children}</div>
);

export const useDashboard = () => dashboardContextValue;
export const DashboardContext =
  {} as unknown as typeof import("../DashboardContext")["DashboardContext"];
