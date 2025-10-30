import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { render, screen, waitFor } from "@testing-library/react";

import AppRouter, { type AppRouterProps } from "../../router/AppRouter";

vi.mock("framer-motion", () => {
  const NoopComponent = ({ children, ...rest }: { children?: React.ReactNode }) => (
    <div {...rest}>{children}</div>
  );

  return {
    __esModule: true,
    motion: new Proxy(
      {},
      {
        get: () => NoopComponent,
      },
    ),
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
  };
});

vi.mock("../../shared/components/Dashboard", () => ({
  __esModule: true,
  default: () => <div data-testid="dashboard-shell">Dashboard</div>,
}));

function LocationProbe(props: React.ComponentProps<typeof AppRouter>) {
  const location = useLocation();

  return (
    <>
      <span data-testid="current-path">{location.pathname}</span>
      <AppRouter {...props} />
    </>
  );
}

describe("Rutas de ventas en AppRouter", () => {
  const baseProps: AppRouterProps = {
    token: "demo-token",
    loading: false,
    error: null,
    theme: "dark",
    themeLabel: "Oscuro",
    onToggleTheme: vi.fn(),
    onLogin: vi.fn(async () => {}),
    onLogout: vi.fn(),
  };

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllEnvs();
  });

  it("redirige /sales a inventario cuando enablePurchasesSales está deshabilitado", async () => {
    vi.stubEnv("VITE_SOFTMOBILE_ENABLE_PURCHASES_SALES", "0");

    render(
      <MemoryRouter initialEntries={["/sales"]}>
        <Routes>
          <Route path="*" element={<LocationProbe {...baseProps} />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("current-path").textContent).toBe("/dashboard/inventory");
    });
  });
});
