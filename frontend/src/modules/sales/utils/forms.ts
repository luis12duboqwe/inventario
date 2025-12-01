// [PACK23-UTILS-FORMS-START]
export function required(v: unknown) { return v !== undefined && v !== null && String(v).trim() !== ""; }
export function emailish(v?: string) { return !v || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v); }
export function phoneish(v?: string) { return !v || /^[0-9+()\-\s]{7,}$/.test(v); }
// [PACK23-UTILS-FORMS-END]
