import { httpClient } from "@api/http";
import { Page } from "../types/common";
import { Customer, CustomerListParams } from "./types";
import { apiMap } from "./apiMap";

export async function listCustomers(params: CustomerListParams): Promise<Page<Customer>> {
  const response = await httpClient.get<Page<Customer>>(apiMap.customers.list, { params });
  return response.data;
}

export async function getCustomer(id: string): Promise<Customer> {
  const response = await httpClient.get<Customer>(apiMap.customers.byId(id));
  return response.data;
}

export async function createCustomer(dto: Omit<Customer, "id">): Promise<Customer> {
  const response = await httpClient.post<Customer>(apiMap.customers.create, dto);
  return response.data;
}

export async function updateCustomer(id: string, dto: Partial<Omit<Customer, "id">>): Promise<Customer> {
  const response = await httpClient.put<Customer>(apiMap.customers.byId(id), dto);
  return response.data;
}
