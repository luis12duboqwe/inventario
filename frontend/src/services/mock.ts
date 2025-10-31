// src/services/mock.ts
import { Page } from "./types/common";
export const sleep = (ms=300)=> new Promise(r=>setTimeout(r,ms));

export function mockPage<T>(items: T[], page=1, pageSize=20): Page<T> {
  return { items, total: items.length, page, pageSize };
}
