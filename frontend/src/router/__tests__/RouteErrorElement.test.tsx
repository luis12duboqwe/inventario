import { render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import RouteErrorElement from "../RouteErrorElement";

// Evitar problemas de hoisting al mockear módulos con dependencias al tope
const { logUISpy } = vi.hoisted(() => ({
  logUISpy: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("../../services/audit", () => ({
  __esModule: true,
  logUI: logUISpy,
}));

describe("RouteErrorElement", () => {
  it("muestra el fallback y registra el alcance del fallo", async () => {
    const router = createMemoryRouter(
      [
        {
          path: "/",
          loader: () => {
            throw new Error("fallo en loader");
          },
          element: <div>OK</div>,
          errorElement: <RouteErrorElement scope="/demo" />, // [PACK36-tests]
        },
      ],
      { initialEntries: ["/"] },
    );

    render(<RouterProvider router={router} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudo cargar la sección");

    await waitFor(() => {
      expect(logUISpy).toHaveBeenCalledWith(
        expect.objectContaining({
          action: "router.error",
          meta: expect.objectContaining({ scope: "/demo" }),
        }),
      );
    });
  });
});
