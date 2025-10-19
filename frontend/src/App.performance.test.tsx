import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App rendimiento inicial", () => {
  it("muestra el formulario de ingreso en menos de 2 segundos", () => {
    const start = performance.now();
    const { unmount } = render(<App />);
    const elapsed = performance.now() - start;

    expect(screen.getByText(/Ingreso seguro/i)).toBeInTheDocument();
    expect(elapsed).toBeLessThan(2000);

    unmount();
  });
});
