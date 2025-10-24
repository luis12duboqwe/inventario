import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import BootstrapForm from "../BootstrapForm";

describe("BootstrapForm", () => {
  it("evita el envío cuando las contraseñas no coinciden", async () => {
    const handleSubmit = vi.fn();
    const user = userEvent.setup();

    render(<BootstrapForm loading={false} error={null} successMessage={null} onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText("Correo corporativo"), "admin@example.com");
    await user.type(screen.getByLabelText("Contraseña"), "Password123!");
    await user.type(screen.getByLabelText("Confirmar contraseña"), "Password123!!");

    await user.click(screen.getByRole("button", { name: "Registrar cuenta" }));

    expect(handleSubmit).not.toHaveBeenCalled();
    expect(screen.getAllByText("Las contraseñas no coinciden.").length).toBeGreaterThan(0);
  });

  it("requiere capturar el correo corporativo antes de enviar", async () => {
    const handleSubmit = vi.fn();
    const user = userEvent.setup();

    render(<BootstrapForm loading={false} error={null} successMessage={null} onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText("Contraseña"), "Password123!");
    await user.type(screen.getByLabelText("Confirmar contraseña"), "Password123!");

    await user.click(screen.getByRole("button", { name: "Registrar cuenta" }));

    expect(handleSubmit).not.toHaveBeenCalled();
    expect(screen.getByText("El correo corporativo es obligatorio.")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Correo corporativo"), "admin@example.com");

    expect(screen.queryByText("El correo corporativo es obligatorio.")).not.toBeInTheDocument();
  });

  it("normaliza los valores antes de enviarlos", async () => {
    const handleSubmit = vi.fn();
    const user = userEvent.setup();

    render(<BootstrapForm loading={false} error={null} successMessage={null} onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText("Correo corporativo"), " admin@example.com ");
    await user.type(screen.getByLabelText("Nombre completo"), " Admin Uno ");
    await user.type(screen.getByLabelText("Teléfono de contacto"), " +123456789 ");
    await user.type(screen.getByLabelText("Contraseña"), "Password123!");
    await user.type(screen.getByLabelText("Confirmar contraseña"), "Password123!");

    await user.click(screen.getByRole("button", { name: "Registrar cuenta" }));

    expect(handleSubmit).toHaveBeenCalledWith({
      username: "admin@example.com",
      fullName: "Admin Uno",
      telefono: "+123456789",
      password: "Password123!",
    });
  });
});
