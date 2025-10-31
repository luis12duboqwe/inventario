#!/usr/bin/env node
import { mkdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

import { chromium } from "playwright";

const DEFAULT_BASE_URL = "http://localhost:5173";
const DEFAULT_OUTPUT = "docs/capturas";
const DEFAULT_WIDTH = 1600;
const DEFAULT_HEIGHT = 900;
const MAX_BLOCK_HEIGHT = 1300;

const MODULES = [
  { slug: "inventario", route: "/dashboard/inventory", label: "Inventario" },
  { slug: "operaciones", route: "/dashboard/operations", label: "Operaciones" },
  { slug: "analitica", route: "/dashboard/analytics", label: "Analítica" },
  { slug: "seguridad", route: "/dashboard/security", label: "Seguridad" },
  { slug: "sincronizacion", route: "/dashboard/sync", label: "Sincronización" },
  { slug: "usuarios", route: "/dashboard/users", label: "Usuarios" },
  { slug: "reparaciones", route: "/dashboard/repairs", label: "Reparaciones" },
];

function parseArgs(argv) {
  const result = new Map();
  for (let index = 0; index < argv.length; index += 1) {
    const current = argv[index];
    if (!current.startsWith("--")) {
      continue;
    }
    const key = current.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      result.set(key, "true");
      continue;
    }
    result.set(key, next);
    index += 1;
  }
  return result;
}

function resolveNumberOption(value, fallback) {
  if (value === undefined) {
    return fallback;
  }
  const parsed = Number.parseInt(String(value), 10);
  if (Number.isNaN(parsed) || parsed <= 0) {
    return fallback;
  }
  return parsed;
}

function buildSegments(totalHeight, blockHeight) {
  if (totalHeight <= blockHeight) {
    return [0];
  }
  const positions = [];
  let offset = 0;
  while (offset + blockHeight < totalHeight) {
    positions.push(offset);
    offset += blockHeight;
  }
  const lastStart = Math.max(0, totalHeight - blockHeight);
  if (positions.length === 0 || positions[positions.length - 1] !== lastStart) {
    positions.push(lastStart);
  }
  return positions;
}

async function ensureBaseLayout(page, blockWidth) {
  await page.addStyleTag({
    content: `
      body {
        margin: 0 !important;
        background: radial-gradient(circle at top, rgba(10,12,18,1) 0%, rgba(9,10,14,1) 28%, rgba(6,7,11,1) 100%) !important;
      }
      .dashboard-shell {
        background: linear-gradient(180deg, rgba(12,14,20,1) 0%, rgba(8,9,13,1) 100%) !important;
      }
      .dashboard-main {
        width: ${blockWidth}px !important;
        max-width: ${blockWidth}px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45) !important;
        border-radius: 20px !important;
        overflow: visible !important;
      }
      .dashboard-main::before,
      .dashboard-main::after {
        display: none !important;
      }
      .dashboard-topbar {
        background-color: rgba(25,25,30,1) !important;
        -webkit-backdrop-filter: none !important;
        backdrop-filter: none !important;
        border-bottom: 1px solid rgba(40,45,60,0.6) !important;
      }
      .dashboard-topbar__actions .dashboard-search,
      .dashboard-topbar__actions .btn.btn--danger,
      .dashboard-topbar__actions .dashboard-mobile-menu {
        display: none !important;
      }
      .dashboard-sidebar-backdrop,
      .modal,
      .tooltip,
      .tooltip-content,
      [role="dialog"],
      [data-overlay],
      .backdrop-blur {
        display: none !important;
      }
      .toast-container,
      .alert.warning,
      .alert.error,
      .alert.info {
        display: none !important;
      }
      .dashboard-content {
        overflow: visible !important;
      }
      .global-metrics__header {
        background-color: rgba(15,18,26,1) !important;
      }
      .dashboard-topbar__titles h1 {
        letter-spacing: 0.02em;
      }
    `,
  });

  await page.evaluate(() => {
    const body = document.body;
    if (body) {
      body.classList.remove("compact-mode");
    }
    document.querySelectorAll(".toast, .alert").forEach((node) => {
      node.remove();
    });
    const overlays = document.querySelectorAll(
      ".dashboard-sidebar-backdrop, .tooltip, [role=dialog], .modal, [data-overlay]",
    );
    overlays.forEach((node) => node.remove());

    const quickHelp = document.querySelector(".dashboard-topbar__actions .btn.btn--ghost");
    if (quickHelp instanceof HTMLButtonElement) {
      quickHelp.blur();
    }
    const searchInput = document.querySelector(".dashboard-topbar__actions input[type=search]");
    if (searchInput instanceof HTMLInputElement) {
      searchInput.value = "";
      searchInput.blur();
    }
  });
}

async function scrollToModuleOffset(page, offset) {
  await page.evaluate((value) => {
    const main = document.querySelector(".dashboard-main");
    if (!(main instanceof HTMLElement)) {
      throw new Error("No se encontró el contenedor principal del dashboard");
    }
    const top = main.getBoundingClientRect().top + window.scrollY;
    window.scrollTo({ top: top + value, behavior: "instant" });
  }, offset);
  await page.waitForTimeout(200);
}

async function computeClipArea(page, width, height) {
  return page.evaluate(
    ({ w, h }) => {
      const main = document.querySelector(".dashboard-main");
      if (!(main instanceof HTMLElement)) {
        throw new Error("No se encontró el contenedor principal del dashboard");
      }
      const rect = main.getBoundingClientRect();
      const availableHeight = Math.min(h, window.innerHeight - rect.top);
      if (availableHeight < h) {
        window.scrollBy({ top: h - availableHeight, behavior: "instant" });
        const updatedRect = main.getBoundingClientRect();
        return {
          x: Math.max(0, Math.round(updatedRect.left)),
          y: Math.max(0, Math.round(updatedRect.top)),
          width: Math.round(w),
          height: Math.round(h),
        };
      }
      return {
        x: Math.max(0, Math.round(rect.left)),
        y: Math.max(0, Math.round(rect.top)),
        width: Math.round(w),
        height: Math.round(h),
      };
    },
    { w: width, h: height },
  );
}

async function captureModule(page, module, options) {
  const url = `${options.baseUrl.replace(/\/$/, "")}${module.route}`;
  console.info(`→ Capturando ${module.label} (${url})`);

  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForSelector(".dashboard-main", { timeout: options.timeout });
  await page.waitForTimeout(options.settleTime);
  await page.evaluate(() => window.scrollTo(0, 0));

  await ensureBaseLayout(page, options.blockWidth);

  const totalHeight = await page.evaluate(() => {
    const main = document.querySelector(".dashboard-main");
    if (!(main instanceof HTMLElement)) {
      throw new Error("No se encontró el contenedor principal del dashboard");
    }
    return Math.ceil(main.scrollHeight);
  });

  const segments = buildSegments(totalHeight, options.blockHeight);
  const files = [];

  for (let index = 0; index < segments.length; index += 1) {
    const offset = segments[index];
    await scrollToModuleOffset(page, offset);
    const clip = await computeClipArea(page, options.blockWidth, options.blockHeight);
    const fileName =
      segments.length === 1
        ? `${module.slug}.png`
        : `${module.slug}-${String(index + 1).padStart(2, "0")}.png`;
    const outputPath = path.join(options.outputDir, fileName);
    await page.screenshot({
      path: outputPath,
      clip,
      animations: "disabled",
      fullPage: false,
      type: "png",
    });
    files.push(outputPath);
    console.info(`   • Bloque ${index + 1}/${segments.length} → ${outputPath}`);
  }

  return files;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const baseUrl = args.get("base-url") ?? process.env.SOFTMOBILE_CAPTURE_BASE_URL ?? DEFAULT_BASE_URL;
  const outputDir = path.resolve(
    process.cwd(),
    args.get("output") ?? process.env.SOFTMOBILE_CAPTURE_DIR ?? DEFAULT_OUTPUT,
  );

  const width = resolveNumberOption(
    args.get("width") ?? process.env.SOFTMOBILE_CAPTURE_WIDTH,
    DEFAULT_WIDTH,
  );
  const desiredHeight = resolveNumberOption(
    args.get("height") ?? process.env.SOFTMOBILE_CAPTURE_HEIGHT,
    DEFAULT_HEIGHT,
  );
  const blockHeight = Math.min(desiredHeight, MAX_BLOCK_HEIGHT);

  const settleTime = resolveNumberOption(
    args.get("settle") ?? process.env.SOFTMOBILE_CAPTURE_WAIT_MS,
    800,
  );
  const timeout = resolveNumberOption(args.get("timeout"), 20000);

  const headless = args.get("headless") !== "false";
  const token = args.get("token") ?? process.env.SOFTMOBILE_CAPTURE_TOKEN ?? "demo-token";

  await mkdir(outputDir, { recursive: true });

  const viewportWidth = Math.max(width + 320, width);
  const viewportHeight = Math.max(blockHeight + 240, blockHeight + 40);

  const browser = await chromium.launch({ headless });
  const context = await browser.newContext({
    viewport: { width: viewportWidth, height: viewportHeight },
    deviceScaleFactor: 1,
    colorScheme: "dark",
  });

  await context.addInitScript((initialToken) => {
    window.localStorage.setItem("softmobile_token", initialToken.token);
    window.localStorage.setItem("softmobile_theme", "dark");
  }, { token });

  const page = await context.newPage();

  const captured = [];
  for (const module of MODULES) {
    const files = await captureModule(page, module, {
      baseUrl,
      outputDir,
      blockWidth: width,
      blockHeight,
      settleTime,
      timeout,
    });
    captured.push({ module: module.label, files });
  }

  await browser.close();

  console.info("\nResumen de capturas:");
  for (const item of captured) {
    for (const file of item.files) {
      console.info(` - ${item.module}: ${file}`);
    }
  }

  console.info("\nFinalizado. Asegúrate de ejecutar 'npx playwright install chromium' la primera vez.");
}

main().catch((error) => {
  console.error("Error generando capturas:", error);
  process.exitCode = 1;
});
