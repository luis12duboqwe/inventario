// Actualizado por Codex el 2025-10-20
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/setupTests.ts",
    restoreMocks: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000/api",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  build: {
    // Forzamos el minificador Terser para obtener bundles más compactos sin perder compatibilidad.
    minify: "terser",
    // Deshabilitamos los sourcemaps en producción para reducir el tamaño final y evitar exponer código fuente.
    sourcemap: false,
    rollupOptions: {
      output: {
        // Dividimos dependencias críticas en chunks dedicados para mejorar el cacheo entre despliegues.
        manualChunks: {
          // React y su DOM virtual quedan en un chunk estable reutilizable.
          react: ["react", "react-dom"],
          // Librerías de gráficos se separan para cargarse bajo demanda en secciones analíticas.
          charts: ["recharts"],
          // El router mantiene su propio bundle para optimizar la navegación basada en rutas.
          router: ["react-router", "react-router-dom"],
          // Conservamos un chunk dedicado para animaciones y efectos visuales pesados.
          analytics: ["framer-motion"],
        },
      },
    },
  },
});
