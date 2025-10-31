import { render, screen } from "@testing-library/react";
import ActionIndicatorBar from "../ActionIndicatorBar";

describe("ActionIndicatorBar", () => {
  it("muestra indicadores de guardado, sincronización y alertas", () => {
    render(
      <ActionIndicatorBar
        loading={false}
        hasSuccessMessage
        hasError={false}
        errorMessage={null}
        syncStatus="Sincronización completa"
        networkAlert={null}
        lastInventoryRefresh={new Date(Date.now() - 2 * 60 * 1000)}
      />,
    );

    expect(screen.getByText("Guardado")).toBeInTheDocument();
    expect(screen.getByText("Sincronización")).toBeInTheDocument();
    expect(screen.getByText("Alertas")).toBeInTheDocument();
    expect(screen.getByText(/Sincronización completa/)).toBeInTheDocument();
    expect(screen.getByText("Cambios confirmados recientemente")).toBeInTheDocument();
    expect(screen.getByText("Sin alertas críticas registradas")).toBeInTheDocument();
  });

  it("alerta sobre errores y red desconectada", () => {
    render(
      <ActionIndicatorBar
        loading
        hasSuccessMessage={false}
        hasError
        errorMessage="Fallo al guardar"
        syncStatus={null}
        networkAlert="Modo sin conexión"
        lastInventoryRefresh={null}
      />,
    );

    expect(screen.getByText("Procesando cambios en curso")).toBeInTheDocument();
    expect(screen.getByText("Modo sin conexión")).toBeInTheDocument();
    expect(screen.getByText("Fallo al guardar")).toBeInTheDocument();
  });
});
