// src/services/sales/quotes.ts
import { httpGet, httpPost, httpPut } from "../http";
import { Page } from "../types/common";
import { Quote, QuoteListParams, QuoteCreate, CheckoutResponse } from "./types";
import { apiMap } from "./apiMap";

export async function listQuotes(params: QuoteListParams): Promise<Page<Quote>> {
  return httpGet<Page<Quote>>(apiMap.quotes.list, { withAuth: true, query: params });
}

export async function getQuote(id: string): Promise<Quote> {
  return httpGet<Quote>(apiMap.quotes.byId(id), { withAuth: true });
}

export async function createQuote(dto: QuoteCreate): Promise<Quote> {
  return httpPost<Quote>(apiMap.quotes.create, dto, { withAuth: true });
}

export async function updateQuote(id: string, dto: Partial<QuoteCreate>): Promise<Quote> {
  return httpPut<Quote>(apiMap.quotes.byId(id), dto, { withAuth: true });
}

export async function convertQuoteToSale(id: string): Promise<CheckoutResponse> {
  return httpPost<CheckoutResponse>(apiMap.quotes.convert(id), {}, { withAuth: true });
}
