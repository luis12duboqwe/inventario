// src/services/sales/products.ts
import { httpGet } from "../http";
import { Page } from "../types/common";
import { Product, ProductSearchParams } from "./types";
import { apiMap } from "./apiMap";

export async function searchProducts(params: ProductSearchParams): Promise<Page<Product>> {
  return httpGet<Page<Product>>(apiMap.products.search, { query: params, withAuth: true });
}

export async function getProductById(id: string): Promise<Product> {
  return httpGet<Product>(apiMap.products.byId(id), { withAuth: true });
}
