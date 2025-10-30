// src/services/sales/returns.ts
import { httpGet, httpPost } from "../http";
import { Page } from "../types/common";
import { ReturnDoc, ReturnListParams, ReturnCreate } from "./types";
import { apiMap } from "./apiMap";

export async function listReturns(params: ReturnListParams): Promise<Page<ReturnDoc>> {
  return httpGet<Page<ReturnDoc>>(apiMap.returns.list, { withAuth: true, query: params });
}

export async function getReturn(id: string): Promise<ReturnDoc> {
  return httpGet<ReturnDoc>(apiMap.returns.byId(id), { withAuth: true });
}

export async function createReturn(dto: ReturnCreate): Promise<ReturnDoc> {
  return httpPost<ReturnDoc>(apiMap.returns.create, dto, { withAuth: true });
}
