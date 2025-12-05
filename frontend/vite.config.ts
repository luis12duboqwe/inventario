import { defineConfig, loadEnv } from "vite";
import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

const DEFAULT_DEV_HOST = "0.0.0.0";
const DEFAULT_DEV_PORT = 5173; // Standard Vite port
const DEFAULT_BACKEND_TARGET = "http://localhost:8000"; // Standard FastAPI port

export default defineConfig(({ mode }) => {
  const envDir = fileURLToPath(new URL(".", import.meta.url));
  const env = loadEnv(mode, envDir, "");
  const devHost = env.VITE_DEV_HOST?.trim() || DEFAULT_DEV_HOST;
  const devPort = Number(env.VITE_DEV_PORT ?? DEFAULT_DEV_PORT);
  const backendTarget = env.VITE_API_URL || DEFAULT_BACKEND_TARGET;

  console.log("[Vite] Proxy '/api' target:", backendTarget);

  return {
    plugins: [
      react(),
      VitePWA({
        registerType: "autoUpdate",
        includeAssets: ["favicon.ico", "apple-touch-icon.png", "masked-icon.svg"],
        manifest: {
          name: "Softmobile 2025",
          short_name: "Softmobile",
          description: "Sistema de Inventario y POS Corporativo",
          theme_color: "#0d1117",
          background_color: "#0d1117",
          display: "standalone",
          icons: [
            {
              src: "pwa-192x192.png",
              sizes: "192x192",
              type: "image/png",
            },
            {
              src: "pwa-512x512.png",
              sizes: "512x512",
              type: "image/png",
            },
            {
              src: "pwa-512x512.png",
              sizes: "512x512",
              type: "image/png",
              purpose: "any maskable",
            },
          ],
        },
        workbox: {
          globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
          runtimeCaching: [
            {
              urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
              handler: "CacheFirst",
              options: {
                cacheName: "google-fonts-cache",
                expiration: {
                  maxEntries: 10,
                  maxAgeSeconds: 60 * 60 * 24 * 365, // <== 365 days
                },
                cacheableResponse: {
                  statuses: [0, 200],
                },
              },
            },
            {
              urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
              handler: "CacheFirst",
              options: {
                cacheName: "gstatic-fonts-cache",
                expiration: {
                  maxEntries: 10,
                  maxAgeSeconds: 60 * 60 * 24 * 365, // <== 365 days
                },
                cacheableResponse: {
                  statuses: [0, 200],
                },
              },
            },
            {
              // Cache API responses for offline access
              urlPattern: /\/api\/.*\/(inventory|products|customers|suppliers|users|config).*/i,
              handler: "NetworkFirst",
              options: {
                cacheName: "api-cache",
                expiration: {
                  maxEntries: 100,
                  maxAgeSeconds: 60 * 60 * 24, // 24 hours
                },
                networkTimeoutSeconds: 10, // Fallback to cache if network takes > 10s
                cacheableResponse: {
                  statuses: [0, 200],
                },
              },
            },
          ],
        },
      }),
    ],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
        "@api": fileURLToPath(new URL("./src/api", import.meta.url)),
        "@components": fileURLToPath(new URL("./src/components", import.meta.url)),
        "@modules": fileURLToPath(new URL("./src/modules", import.meta.url)),
        "@pages": fileURLToPath(new URL("./src/pages", import.meta.url)),
        "@services": fileURLToPath(new URL("./src/services", import.meta.url)),
        "@shared": fileURLToPath(new URL("./src/shared", import.meta.url)),
        "@ui": fileURLToPath(new URL("./src/ui", import.meta.url)),
        "@utils": fileURLToPath(new URL("./src/utils", import.meta.url)),
        "@hooks": fileURLToPath(new URL("./src/hooks", import.meta.url)),
        "@lib": fileURLToPath(new URL("./src/lib", import.meta.url)),
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: "./src/setupTests.ts",
      restoreMocks: true,
      coverage: {
        provider: "v8",
        reporter: ["text", "json", "html"],
        exclude: ["node_modules/", "src/setupTests.ts"],
      },
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
          configure(proxy) {
            proxy.on("error", (err) => {
              console.error("[Vite proxy] error:", err?.message || err);
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
