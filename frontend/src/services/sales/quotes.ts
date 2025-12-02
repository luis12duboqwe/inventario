import { httpClient } from "@api/http";
import { Page } from "../types/common";
import { Quote, QuoteListParams, QuoteCreate, CheckoutResponse } from "./types";
import { apiMap } from "./apiMap";

export async function listQuotes(params: QuoteListParams): Promise<Page<Quote>> {
  const response = await httpClient.get<Page<Quote>>(apiMap.quotes.list, { params });
  return response.data;
}

export async function getQuote(id: string): Promise<Quote> {
  const response = await httpClient.get<Quote>(apiMap.quotes.byId(id));
  return response.data;
}

export async function createQuote(dto: QuoteCreate): Promise<Quote> {
  const response = await httpClient.post<Quote>(apiMap.quotes.create, dto);
  return response.data;
}

export async function updateQuote(id: string, dto: Partial<QuoteCreate>): Promise<Quote> {
  const response = await httpClient.put<Quote>(apiMap.quotes.byId(id), dto);
  return response.data;
}

export async function convertQuoteToSale(id: string): Promise<CheckoutResponse> {
  const response = await httpClient.post<CheckoutResponse>(apiMap.quotes.convert(id), {});
  return response.data;
}
