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
      isActive: true,
      srHint: "Módulo abierto actualmente.",
    },
    {
      to: "/dashboard/analytics",
      label: "Analítica",
      description: "Consulta indicadores estratégicos.",
      icon: <BarChart3 aria-hidden="true" />,
      isActive: false,
    },
  ];

  it("muestra los módulos disponibles y notificaciones activas", () => {
    render(
      <MemoryRouter>
        <AdminControlPanel
          modules={modules}
          roleVariant="admin"
          notifications={2}
          notificationItems={[
            {
              id: "notif-1",
              title: "Operación",
              description: "Se guardaron los cambios",
              variant: "success",
            },
          ]}
        />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Centro de control Softmobile" })).toBeInTheDocument();
    expect(screen.getByText("Gestiona existencias y auditorías en vivo.")).toBeInTheDocument();
    expect(screen.getByText("Consulta indicadores estratégicos.")).toBeInTheDocument();
    expect(screen.getByText("2 notificaciones activas")).toBeInTheDocument();
    expect(screen.getByText("Se guardaron los cambios")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Inventario/ })).toHaveAttribute("aria-current", "page");
  });

  it("indica cuando no hay notificaciones pendientes", () => {
    render(
      <MemoryRouter>
        <AdminControlPanel
          modules={modules.map((module, index) => ({
            ...module,
            isActive: index === 0,
          }))}
          roleVariant="operator"
          notifications={0}
          notificationItems={[]}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("Sin notificaciones pendientes")).toBeInTheDocument();
    expect(screen.getByText("No hay notificaciones activas.")).toBeInTheDocument();
  });
});
