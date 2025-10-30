import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuditPage from "../AuditPage";
import { AuthzProvider } from "../../../../auth/useAuthz";

const downloadBlobMock = vi.hoisted(() => vi.fn());
const fetchAuditEventsMock = vi.hoisted(() => vi.fn());
const downloadAuditExportMock = vi.hoisted(() => vi.fn());

vi.mock("../../../../lib/download", () => ({
  downloadBlob: downloadBlobMock,
}));

vi.mock("../../../../services/audit", () => ({
  fetchAuditEvents: fetchAuditEventsMock,
  downloadAuditExport: downloadAuditExportMock,
}));

const sampleResponse = {
  items: [
    {
      ts: "2025-03-01T10:00:00.000Z",
      userId: "auditor",
      module: "POS",
      action: "checkout",
      entityId: "sale-1",
      meta: { total: 120 },
    },
  ],
  total: 1,
  limit: 100,
  offset: 0,
  has_more: false,
};

describe("AuditPage", () => {
  const renderWithAuth = () =>
    render(
      <AuthzProvider user={{ id: "1", name: "Auditor", role: "ADMIN" }}>
        <AuditPage />
      </AuthzProvider>,
    );

  beforeEach(() => {
    fetchAuditEventsMock.mockReset();
    downloadAuditExportMock.mockReset();
    downloadBlobMock.mockReset();
    localStorage.clear();
  });

  it("muestra registros provenientes del backend", async () => {
    fetchAuditEventsMock.mockResolvedValue(sampleResponse);

    renderWithAuth();

    expect(await screen.findByText("auditor")).toBeInTheDocument();
    expect(screen.getByText("checkout")).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchAuditEventsMock).toHaveBeenCalledWith({ limit: 100, offset: 0 });
    });
  });

  it("recupera la cola local cuando la API no responde", async () => {
    const queued = [{ ts: Date.now(), userId: "offline", module: "POS", action: "hold" }];
    localStorage.setItem("sm_ui_audit_queue", JSON.stringify(queued));
    fetchAuditEventsMock.mockRejectedValue(new Error("offline"));

    renderWithAuth();

    const offlineMentions = await screen.findAllByText("offline");
    expect(offlineMentions.length).toBeGreaterThan(0);
    await waitFor(() => expect(screen.queryByText("Cargando…")).not.toBeInTheDocument());
    expect(screen.getByText("hold")).toBeInTheDocument();
  });

  it("descarga exportaciones usando el servicio dedicado", async () => {
    fetchAuditEventsMock.mockResolvedValue(sampleResponse);
    downloadAuditExportMock.mockResolvedValue({
      filename: "audit-ui.csv",
      blob: new Blob(["data"], { type: "text/csv" }),
    });

    renderWithAuth();

    const exportButton = await screen.findByRole("button", { name: /Exportar CSV/i });
    await userEvent.click(exportButton);

    await waitFor(() => {
      expect(downloadAuditExportMock).toHaveBeenCalledWith("csv", { limit: 100, offset: 0 });
      expect(downloadBlobMock).toHaveBeenCalled();
    });
  });
});
