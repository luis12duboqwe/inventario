import {
  listPriceLists,
  getPriceList,
  createPriceList,
  updatePriceList,
  deletePriceList,
  createPriceListItem,
  updatePriceListItem,
  deletePriceListItem,
  getPriceListItem,
  resolveDevicePrice,
  type PriceList,
  type PriceListCreateInput,
  type PriceListUpdateInput,
  type PriceListItem,
  type PriceListItemCreateInput,
  type PriceListItemUpdateInput,
  type PriceListListParams,
  type PriceResolution,
  type PriceResolutionParams,
} from "@api/pricing";

export const priceListsService = {
  list: (
    token: string,
    params: PriceListListParams = {},
    reason?: string,
  ): Promise<PriceList[]> => listPriceLists(token, params, reason),
  get: (
    token: string,
    priceListId: number,
    options: { includeItems?: boolean } = {},
    reason?: string,
  ): Promise<PriceList> => getPriceList(token, priceListId, options, reason),
  create: (
    token: string,
    payload: PriceListCreateInput,
    reason: string,
  ): Promise<PriceList> => createPriceList(token, payload, reason),
  update: (
    token: string,
    priceListId: number,
    payload: PriceListUpdateInput,
    reason: string,
  ): Promise<PriceList> => updatePriceList(token, priceListId, payload, reason),
  remove: (token: string, priceListId: number, reason: string): Promise<void> =>
    deletePriceList(token, priceListId, reason),
  addItem: (
    token: string,
    priceListId: number,
    payload: PriceListItemCreateInput,
    reason: string,
  ): Promise<PriceListItem> => createPriceListItem(token, priceListId, payload, reason),
  updateItem: (
    token: string,
    itemId: number,
    payload: PriceListItemUpdateInput,
    reason: string,
  ): Promise<PriceListItem> => updatePriceListItem(token, itemId, payload, reason),
  removeItem: (token: string, itemId: number, reason: string): Promise<void> =>
    deletePriceListItem(token, itemId, reason),
  getItem: (token: string, itemId: number, reason?: string): Promise<PriceListItem> =>
    getPriceListItem(token, itemId, reason),
  resolve: (
    token: string,
    params: PriceResolutionParams,
    reason?: string,
  ): Promise<PriceResolution | null> => resolveDevicePrice(token, params, reason),
};

export type { PriceList, PriceListItem, PriceResolution };
export type {
  PriceListCreateInput,
  PriceListUpdateInput,
  PriceListItemCreateInput,
  PriceListItemUpdateInput,
  PriceListListParams,
  PriceResolutionParams,
};
