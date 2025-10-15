import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, beforeAll, beforeEach, afterEach, expect, it, vi } from "vitest";
import type { AuditLogEntry, AuditReminderEntry, AuditReminderSummary } from "../../../../api";

const pushToastMock = vi.fn();
const getAuditLogsMock = vi.fn<(token: string, filters?: unknown) => Promise<AuditLogEntry[]>>();
const getAuditRemindersMock = vi.fn<(token: string) => Promise<AuditReminderSummary>>();
const exportAuditLogsCsvMock = vi.fn<(token: string, filters: unknown, reason: string) => Promise<Blob>>();
const downloadAuditPdfMock = vi.fn<(token: string, filters: unknown, reason: string) => Promise<Blob>>();
const acknowledgeAuditAlertMock = vi.fn<
  (token: string, payload: { entity_type: string; entity_id: string; note?: string }, reason: string) => Promise<unknown>
>();
const promptMock = vi.fn();

vi.stubGlobal("prompt", promptMock);

const dashboardContextModuleId = vi.hoisted(() =>
  new URL("../../../dashboard/context/DashboardContext.tsx", import.meta.url).pathname
);

const mockDashboardModule = vi.hoisted(() =>
  () => ({
    __esModule: true,
    useDashboard: () => ({
      pushToast: pushToastMock,
    }) as ReturnType<typeof import("../../../dashboard/context/DashboardContext").useDashboard>,
  })
);

vi.mock("../../dashboard/context/DashboardContext", mockDashboardModule);
vi.mock("../../../dashboard/context/DashboardContext", mockDashboardModule);
vi.mock("../../dashboard/context/DashboardContext.tsx", mockDashboardModule);
vi.mock("../../../dashboard/context/DashboardContext.tsx", mockDashboardModule);
vi.mock(dashboardContextModuleId, mockDashboardModule);

vi.mock("../../../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../../api")>();
  return {
    ...actual,
    getAuditLogs: getAuditLogsMock,
    getAuditReminders: getAuditRemindersMock,
    exportAuditLogsCsv: exportAuditLogsCsvMock,
    downloadAuditPdf: downloadAuditPdfMock,
    acknowledgeAuditAlert: acknowledgeAuditAlertMock,
  };
});

const defaultLog = (overrides: Partial<AuditLogEntry> = {}): AuditLogEntry => ({
  id: 1,
  action: "sale_registered",
  entity_type: "sale",
  entity_id: "1001",
  details: "Venta POS",
  created_at: "2025-02-28T08:00:00.000Z",
  severity: "warning",
  severity_label: "Preventiva",
  ...overrides,
});

const defaultReminder = (overrides: Partial<AuditReminderEntry> = {}): AuditReminderEntry => ({
  entity_type: "pos_sale",
  entity_id: "2002",
  first_seen: "2025-02-28T07:00:00.000Z",
  last_seen: "2025-02-28T08:55:00.000Z",
  occurrences: 3,
  latest_action: "sale_registered",
  latest_details: "Venta con descuento",
  status: "pending",
  acknowledged_at: null,
  acknowledged_by_id: null,
  acknowledged_by_name: null,
  acknowledged_note: null,
  ...overrides,
});

const buildReminderSummary = (entries: AuditReminderEntry[], overrides: Partial<AuditReminderSummary> = {}): AuditReminderSummary => ({
  threshold_minutes: 15,
  min_occurrences: 2,
  total: entries.length,
  pending_count: entries.filter((entry) => entry.status === "pending").length,
  acknowledged_count: entries.filter((entry) => entry.status === "acknowledged").length,
  persistent: entries,
  ...overrides,
});

const originalCreateObjectURL = URL.createObjectURL;
const originalRevokeObjectURL = URL.revokeObjectURL;

let AuditLogComponent: typeof import("../AuditLog").default;

beforeAll(async () => {
  const module = await import("../AuditLog");
  AuditLogComponent = module.default;
});

describe("AuditLog", () => {
  beforeEach(() => {
    pushToastMock.mockReset();
    getAuditLogsMock.mockReset();
    getAuditRemindersMock.mockReset();
    exportAuditLogsCsvMock.mockReset();
    downloadAuditPdfMock.mockReset();
    acknowledgeAuditAlertMock.mockReset();
    promptMock.mockReset();

    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:mock"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => {
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: originalCreateObjectURL,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: originalRevokeObjectURL,
    });
  });

  it("muestra las métricas iniciales de recordatorios y logs", async () => {
    getAuditLogsMock.mockResolvedValue([defaultLog()]);
    const reminders = [
      defaultReminder(),
      defaultReminder({
        entity_id: "2003",
        status: "acknowledged",
        acknowledged_at: "2025-02-28T08:40:00.000Z",
        acknowledged_by_name: "Admin Seguridad",
        acknowledged_note: "Revisión manual",
      }),
    ];
    getAuditRemindersMock.mockResolvedValue(buildReminderSummary(reminders));

    render(<AuditLogComponent token="token-123" />);

    await waitFor(() => {
      expect(getAuditLogsMock).toHaveBeenCalledTimes(1);
    });

    expect(await screen.findByText("Pendientes: 1")).toBeInTheDocument();
    expect(screen.getByText("Atendidas: 1")).toBeInTheDocument();
    const logEntries = await screen.findAllByText(/sale_registered/i);
    expect(logEntries.length).toBeGreaterThan(0);
    expect(pushToastMock).toHaveBeenCalled();
  });

  it("solicita el motivo corporativo antes de exportar CSV", async () => {
    getAuditLogsMock.mockResolvedValue([defaultLog()]);
    getAuditRemindersMock.mockResolvedValue(buildReminderSummary([defaultReminder()]));
    exportAuditLogsCsvMock.mockResolvedValue(new Blob(["contenido"], { type: "text/csv" }));
    promptMock.mockReturnValue("Revisión auditoría");

    render(<AuditLogComponent token="token-xyz" />);

    const downloadButton = await screen.findByRole("button", { name: /Descargar CSV/i });
    await userEvent.click(downloadButton);

    await waitFor(() => {
      expect(exportAuditLogsCsvMock).toHaveBeenCalledWith(
        "token-xyz",
        expect.objectContaining({ limit: 50 }),
        "Revisión auditoría"
      );
    });
    expect(pushToastMock).toHaveBeenCalledWith(
      expect.objectContaining({ message: expect.stringContaining("Descarga generada"), variant: "success" })
    );
  });

  it("valida y registra un acuse con motivo corporativo", async () => {
    getAuditLogsMock.mockResolvedValue([defaultLog({ id: 10 })]);
    const pending = defaultReminder({ entity_id: "5001" });
    const acknowledged = defaultReminder({
      entity_id: "5002",
      status: "acknowledged",
      acknowledged_at: "2025-02-28T08:15:00.000Z",
      acknowledged_by_name: "Soporte QA",
      acknowledged_note: "Incidencia controlada",
    });
    getAuditRemindersMock
      .mockResolvedValueOnce(buildReminderSummary([pending, acknowledged]))
      .mockResolvedValueOnce(
        buildReminderSummary([
          {
            ...pending,
            status: "acknowledged",
            acknowledged_at: "2025-02-28T09:05:00.000Z",
            acknowledged_by_name: "Equipo Seguridad",
            acknowledged_note: "Se ajustó POS",
          },
          acknowledged,
        ])
      );
    acknowledgeAuditAlertMock.mockResolvedValue({});

    render(<AuditLogComponent token="token-safe" />);

    const ackButton = await screen.findByRole("button", { name: /Registrar acuse/i });
    await userEvent.click(ackButton);

    const reasonInput = screen.getByLabelText(/Motivo corporativo/i);
    const noteTextarea = screen.getByLabelText(/Nota corporativa/i);

    await userEvent.type(reasonInput, "abc");
    await userEvent.click(screen.getByRole("button", { name: /Guardar acuse/i }));
    expect(await screen.findByText(/debe tener al menos 5 caracteres/i)).toBeInTheDocument();

    await userEvent.clear(reasonInput);
    await userEvent.type(reasonInput, "Revisión manual en sitio");
    await userEvent.type(noteTextarea, "Se notificó al gerente");

    await userEvent.click(screen.getByRole("button", { name: /Guardar acuse/i }));

    await waitFor(() => {
      expect(acknowledgeAuditAlertMock).toHaveBeenCalledWith(
        "token-safe",
        {
          entity_type: pending.entity_type,
          entity_id: pending.entity_id,
          note: "Se notificó al gerente",
        },
        "Revisión manual en sitio"
      );
    });

    expect(pushToastMock).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining(`Acuse registrado para ${pending.entity_type} #${pending.entity_id}`),
        variant: "success",
      })
    );
    expect(getAuditRemindersMock).toHaveBeenCalledTimes(2);
  });
});
