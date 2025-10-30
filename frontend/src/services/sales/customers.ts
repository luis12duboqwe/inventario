// src/services/sales/customers.ts
import { httpGet, httpPost, httpPut } from "@/services/http";
import { Page } from "@/services/types/common";
import { Customer, CustomerListParams } from "./types";
import { apiMap } from "./apiMap";

export async function listCustomers(params: CustomerListParams): Promise<Page<Customer>> {
  return httpGet<Page<Customer>>(apiMap.customers.list, { withAuth: true, query: params });
}

export async function getCustomer(id: string): Promise<Customer> {
  return httpGet<Customer>(apiMap.customers.byId(id), { withAuth: true });
}

export async function createCustomer(dto: Omit<Customer, "id">, reason: string): Promise<Customer> {
  return httpPost<Customer>(apiMap.customers.create, dto, {
    withAuth: true,
    headers: { "X-Reason": reason },
  });
}

export async function updateCustomer(
  id: string,
  dto: Partial<Omit<Customer, "id">>,
  reason: string,
): Promise<Customer> {
  return httpPut<Customer>(apiMap.customers.byId(id), dto, {
    withAuth: true,
    headers: { "X-Reason": reason },
  });
}
