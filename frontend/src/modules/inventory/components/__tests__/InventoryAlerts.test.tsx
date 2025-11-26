import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import InventoryAlerts from "../InventoryAlerts";

describe("InventoryAlerts", () => {
  const formatCurrency = (value: number) => `$${value.toFixed(2)}`;

  const baseSettings = {
    threshold: 5,
    minimum_threshold: 0,
    maximum_threshold: 50,
    warning_cutoff: 3,
    critical_cutoff: 1,
    adjustment_variance_threshold: 4,
  };

  it("muestra resumen y elementos con severidad", () => {
    render(
      <InventoryAlerts
        items={[
          {
            device_id: 1,
            store_id: 1,
            store_name: "Central",
            sku: "AL-001",
            name: "Teléfono A",
            quantity: 1,
            unit_price: 120,
            inventory_value: 120,
            severity: "critical",
          },
          {
            device_id: 2,
            store_id: 1,
            store_name: "Central",
            sku: "AL-002",
            name: "Teléfono B",
            quantity: 3,
            unit_price: 90,
            inventory_value: 270,
            severity: "warning",
          },
        ]}
        summary={{ total: 2, critical: 1, warning: 1, notice: 0 }}
        settings={baseSettings}
        thresholdDraft={5}
        onThresholdChange={vi.fn()}
        onSaveThreshold={vi.fn()}
        isSaving={false}
        formatCurrency={formatCurrency}
      />,
    );

    expect(screen.getByText("Total: 2")).toBeInTheDocument();
    expect(screen.getByText("Críticas: 1")).toBeInTheDocument();
    expect(screen.getByText("Advertencias: 1")).toBeInTheDocument();
    expect(screen.getByText("Seguimiento: 0")).toBeInTheDocument();

    expect(screen.getByText(/Teléfono A/)).toBeInTheDocument();
    expect(screen.getByText("Severidad: Crítica")).toBeInTheDocument();
    expect(screen.getByText("$120.00")).toBeInTheDocument();
    expect(screen.getByText(/Teléfono B/)).toBeInTheDocument();
    expect(screen.getByText("Severidad: Advertencia")).toBeInTheDocument();
  });

  it("emite cambios de umbral desde el deslizador y el campo numérico", async () => {
    const onThresholdChange = vi.fn();
    render(
      <InventoryAlerts
        items={[]}
        summary={{ total: 0, critical: 0, warning: 0, notice: 0 }}
        settings={baseSettings}
        thresholdDraft={5}
        onThresholdChange={onThresholdChange}
        onSaveThreshold={vi.fn()}
        isSaving={false}
        formatCurrency={formatCurrency}
      />,
    );

    const slider = screen.getByRole("slider");
    fireEvent.change(slider, { target: { value: "8" } });
    expect(onThresholdChange).toHaveBeenLastCalledWith(8);

    const input = screen.getByRole("spinbutton");
    const user = userEvent.setup();
    await user.clear(input);
    await user.type(input, "120");
    expect(onThresholdChange).toHaveBeenLastCalledWith(baseSettings.maximum_threshold);
  });

  it("muestra estado de guardado y mensaje vacío", () => {
    render(
      <InventoryAlerts
        items={[]}
        summary={{ total: 0, critical: 0, warning: 0, notice: 0 }}
        settings={baseSettings}
        thresholdDraft={5}
        onThresholdChange={vi.fn()}
        onSaveThreshold={vi.fn()}
        isSaving={true}
        formatCurrency={formatCurrency}
      />,
    );

    expect(screen.getByText("Guardando…")).toBeInTheDocument();
    expect(screen.getByText("No hay alertas con el umbral configurado.")).toBeInTheDocument();
  });

  it("usa valores predeterminados cuando faltan métricas y protege cálculos", () => {
    render(
      <InventoryAlerts
        items={[
          {
            device_id: 3,
            store_id: 2,
            store_name: "Norte",
            sku: "AL-003",
            name: "Teléfono C",
            quantity: 2,
            unit_price: 100,
            inventory_value: 200,
            severity: "notice",
            average_daily_sales: undefined as unknown as number,
            projected_days: null,
            minimum_stock: 1,
            reorder_point: 2,
            reorder_gap: 0,
            insights: [],
          },
        ]}
        summary={{
          total: undefined as unknown as number,
          critical: null as unknown as number,
          warning: undefined as unknown as number,
          notice: undefined as unknown as number,
        }}
        settings={baseSettings}
        thresholdDraft={5}
        onThresholdChange={vi.fn()}
        onSaveThreshold={vi.fn()}
        isSaving={false}
        formatCurrency={formatCurrency}
      />,
    );

    expect(screen.getByText("Total: 0")).toBeInTheDocument();
    expect(screen.getByText("Críticas: 0")).toBeInTheDocument();
    expect(screen.getByText("Advertencias: 0")).toBeInTheDocument();
    expect(screen.getByText("Seguimiento: 0")).toBeInTheDocument();
    expect(screen.queryByText(/Venta diaria/)).not.toBeInTheDocument();
  });

  it("indica cuando está cargando las alertas", () => {
    render(
      <InventoryAlerts
        items={[]}
        summary={{ total: 0, critical: 0, warning: 0, notice: 0 }}
        settings={baseSettings}
        thresholdDraft={5}
        onThresholdChange={vi.fn()}
        onSaveThreshold={vi.fn()}
        isSaving={false}
        formatCurrency={formatCurrency}
        isLoading
      />,
    );

    expect(screen.getByText("Cargando alertas…")).toBeInTheDocument();
  });
});
