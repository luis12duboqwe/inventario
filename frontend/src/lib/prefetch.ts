// [PACK25-PREFETCH-START]
export function preimport<T>(loader: () => Promise<T>) { loader().catch(() => { /* ignore */ }); }

export function prefetchJson(url: string) {
  try {
    const ctrl = new AbortController();
    const id = setTimeout(()=>ctrl.abort(), 4000);
    fetch(url, { signal: ctrl.signal, headers:{Accept:"application/json"} })
      .finally(()=>clearTimeout(id));
  } catch {}
}
// [PACK25-PREFETCH-END]
