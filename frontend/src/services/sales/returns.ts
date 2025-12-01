import { httpClient } from "@api/http";
import { Page } from "../types/common";
import { ReturnDoc, ReturnListParams, ReturnCreate } from "./types";
import { apiMap } from "./apiMap";

export async function listReturns(params: ReturnListParams): Promise<Page<ReturnDoc>> {
  const response = await httpClient.get<Page<ReturnDoc>>(apiMap.returns.list, { params });
  return response.data;
}

export async function getReturn(id: string): Promise<ReturnDoc> {
  const response = await httpClient.get<ReturnDoc>(apiMap.returns.byId(id));
  return response.data;
}

export async function createReturn(dto: ReturnCreate): Promise<ReturnDoc> {
  const response = await httpClient.post<ReturnDoc>(apiMap.returns.create, dto);
  return response.data;
}
