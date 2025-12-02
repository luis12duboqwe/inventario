interface PerformanceEntryLCP extends PerformanceEntry {
  value: number;
}

interface PerformanceEntryFID extends PerformanceEntry {
  processingStart: number;
}

interface PerformanceObserverInitWithType {
  type: string;
  buffered?: boolean;
}

export type MetricEvent =
  | { name: "LCP"; value: number; ts: number }
  | { name: "FID"; value: number; ts: number }
  | { name: "TTFB"; value: number; ts: number };

function post(event: MetricEvent) {
  try {
    const json = JSON.stringify({ ...event, type: "web_vitals_lite" });
    // En modo desarrollo, evitamos enviar a la red para no provocar 405.
    if (import.meta.env.DEV) {
      console.debug("[web-vitals-dev]", json);
      return;
    }
    // En producción, si existe `sendBeacon`, enviar al colector corporativo (ajustar destino real).
    if (navigator?.sendBeacon) {
      const blob = new Blob([json], { type: "application/json" });
      navigator.sendBeacon("/api/observability/web-vitals", blob);
      return;
    }
    // console.log("[metrics]", json);
  } catch {}
}

export function startWebVitalsLite() {
  // LCP
  try {
    const po = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const last = entries[entries.length - 1] as unknown as PerformanceEntryLCP;
      if (last && last.value) post({ name: "LCP", value: last.value, ts: Date.now() });
    });
    po.observe({ type: "largest-contentful-paint", buffered: true } as unknown as PerformanceObserverInitWithType);
  } catch {}

  // FID
  try {
    const po = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const first = entries[0] as unknown as PerformanceEntryFID;
      if (first && typeof first.processingStart === "number") {
        const value = first.processingStart - first.startTime;
        post({ name: "FID", value, ts: Date.now() });
      }
    });
    po.observe({ type: "first-input", buffered: true } as unknown as PerformanceObserverInitWithType);
  } catch {}

  // TTFB (aprox)
  try {
    const [nav] = performance.getEntriesByType("navigation") as PerformanceNavigationTiming[];
    if (nav) {
      post({ name: "TTFB", value: nav.responseStart, ts: Date.now() });
    }
  } catch {}
}
