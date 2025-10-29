import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App rendimiento inicial", () => {
  it("muestra el formulario de ingreso en menos de 2 segundos", async () => {
    const start = performance.now();
    const queryClient = new QueryClient();
    const { unmount } = render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>,
    );

    const loginHeading = await screen.findByText(/Ingreso seguro/i, undefined, { timeout: 2000 });
    const elapsed = performance.now() - start;

    expect(loginHeading).toBeInTheDocument();
    expect(elapsed).toBeLessThan(2000);

    unmount();
  });
});
