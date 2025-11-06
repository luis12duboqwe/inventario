import { defineConfig, loadEnv } from "vite";
import { fileURLToPath, URL } from "node:url"; // [PACK37-frontend]
import react from "@vitejs/plugin-react";

const DEFAULT_DEV_HOST = "0.0.0.0";
const DEFAULT_DEV_PORT = 5173;
const DEFAULT_BACKEND_TARGET = "http://127.0.0.1:8000";

export default defineConfig(({ mode }) => {
  // Evita depender de "process" en este archivo de configuración
  const envDir = fileURLToPath(new URL(".", import.meta.url));
  const env = loadEnv(mode, envDir, "");
  const devHost = env.VITE_DEV_HOST?.trim() || DEFAULT_DEV_HOST;
  const devPort = Number(env.VITE_DEV_PORT ?? DEFAULT_DEV_PORT);
  const backendTarget = env.VITE_BACKEND_TARGET?.trim() || DEFAULT_BACKEND_TARGET;

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)), // [PACK37-frontend]
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: "./src/setupTests.ts",
      restoreMocks: true,
    },
    server: {
      host: devHost,
      port: devPort,
      strictPort: true,
      proxy: {
        "/api": {
          target: backendTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
          ws: true,
          // Habilitamos cabeceras reenviadas y timeouts más generosos para evitar 500 del proxy
          // en equipos lentos o recargas en caliente.
          configure(proxy) {
            proxy.on("error", (err) => {
              // Log simple en consola para depurar problemas de proxy en desarrollo
              console.error("[Vite proxy] error:", err?.message || err);
            });
            proxy.on("proxyReq", (proxyReq, req) => {
              // Propaga el host de desarrollo para diagnósticos
              if (req.headers.host) proxyReq.setHeader("X-Forwarded-Host", String(req.headers.host));
            });
          },
        },
      },
    },
    build: {
      minify: "terser",
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks: {
            react: ["react", "react-dom"],
            charts: ["recharts"],
            router: ["react-router", "react-router-dom"],
          },
        },
      },
    },
  };
});
