export type MetricEvent =
  | { name: "LCP"; value: number; ts: number }
  | { name: "FID"; value: number; ts: number }
  | { name: "TTFB"; value: number; ts: number };

function post(event: MetricEvent) {
  try {
    const json = JSON.stringify({ ...event, type: "web_vitals_lite" });
    if (navigator?.sendBeacon) {
      const blob = new Blob([json], { type: "application/json" });
      navigator.sendBeacon("/api/metrics", blob);
    } else {
      console.log("[metrics]", json);
    }
  } catch {}
}

export function startWebVitalsLite() {
  // LCP
  try {
    const po = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const last = entries[entries.length - 1] as any;
      if (last && last.value) post({ name: "LCP", value: last.value, ts: Date.now() });
    });
    po.observe({ type: "largest-contentful-paint", buffered: true } as any);
  } catch {}

  // FID
  try {
    const po = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const first = entries[0] as any;
      if (first && typeof first.processingStart === "number") {
        const value = first.processingStart - first.startTime;
        post({ name: "FID", value, ts: Date.now() });
      }
    });
    po.observe({ type: "first-input", buffered: true } as any);
  } catch {}

  // TTFB (aprox)
  try {
    const [nav] = performance.getEntriesByType("navigation") as PerformanceNavigationTiming[];
    if (nav) {
      post({ name: "TTFB", value: nav.responseStart, ts: Date.now() });
    }
  } catch {}
}
