import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Boxes, BarChart3 } from "lucide-react";
import AdminControlPanel from "../AdminControlPanel";

describe("AdminControlPanel", () => {
  const modules = [
    {
      to: "/dashboard/inventory",
      label: "Inventario",
      description: "Gestiona existencias y auditorías en vivo.",
      icon: <Boxes aria-hidden="true" />,
    },
    {
      to: "/dashboard/analytics",
      label: "Analítica",
      description: "Consulta indicadores estratégicos.",
      icon: <BarChart3 aria-hidden="true" />,
    },
  ];

  it("muestra los módulos disponibles y notificaciones activas", () => {
    render(
      <MemoryRouter>
        <AdminControlPanel modules={modules} roleVariant="admin" notifications={2} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Centro de control Softmobile" })).toBeInTheDocument();
    expect(screen.getByText("Gestiona existencias y auditorías en vivo.")).toBeInTheDocument();
    expect(screen.getByText("Consulta indicadores estratégicos.")).toBeInTheDocument();
    expect(screen.getByText("2 notificaciones activas")).toBeInTheDocument();
  });

  it("indica cuando no hay notificaciones pendientes", () => {
    render(
      <MemoryRouter>
        <AdminControlPanel modules={modules} roleVariant="operator" notifications={0} />
      </MemoryRouter>,
    );

    expect(screen.getByText("Sin notificaciones pendientes")).toBeInTheDocument();
  });
});
