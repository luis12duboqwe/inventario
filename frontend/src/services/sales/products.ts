import { httpClient } from "@api/http";
import { Page } from "../types/common";
import { Product, ProductSearchParams } from "./types";
import { apiMap } from "./apiMap";

export async function searchProducts(params: ProductSearchParams): Promise<Page<Product>> {
  const response = await httpClient.get<Page<Product>>(apiMap.products.search, { params });
  return response.data;
}

export async function getProductById(id: string): Promise<Product> {
  const response = await httpClient.get<Product>(apiMap.products.byId(id));
  return response.data;
}
