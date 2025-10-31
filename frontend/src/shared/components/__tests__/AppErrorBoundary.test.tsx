import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AppErrorBoundary from "../AppErrorBoundary";

// [PACK36-tests]

function ThrowSwitch({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error("fallo controlado");
  }
  return <span>Componente estable</span>;
}

describe("AppErrorBoundary", () => {
  it("muestra la UI de contingencia y permite reintentar", async () => {
    const user = userEvent.setup();

    const { rerender } = render(
      <AppErrorBoundary>
        <ThrowSwitch shouldThrow />
      </AppErrorBoundary>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Algo salió mal");
    expect(screen.getByText("Se produjo un error inesperado al mostrar esta sección.")).toBeInTheDocument();

    rerender(
      <AppErrorBoundary>
        <ThrowSwitch shouldThrow={false} />
      </AppErrorBoundary>,
    );

    await user.click(screen.getByRole("button", { name: "Reintentar" }));

    expect(screen.getByText("Componente estable")).toBeInTheDocument();
  });
});
