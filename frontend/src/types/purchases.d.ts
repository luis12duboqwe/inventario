export type PurchaseForm = {
  storeId: number | null;
  supplier: string;
  deviceId: number | null;
  quantity: number;
  unitCost: number;
};

export type PurchaseRecordForm = {
  storeId: number | null;
  vendorId: number | null;
  paymentMethod: string;
  status: string;
  taxRate: number;
  date: string;
};

export type PurchaseRecordDraftItem = {
  tempId: string;
  productId: number | null;
  quantity: number;
  unitCost: number;
};

export type PurchaseRecordFilters = {
  vendorId: string;
  userId: string;
  dateFrom: string;
  dateTo: string;
  status: string;
  search: string;
};

export type VendorFilters = {
  query: string;
  status: string;
};

export type VendorForm = {
  nombre: string;
  telefono: string;
  correo: string;
  direccion: string;
  tipo: string;
  notas: string;
};

export type VendorHistoryFilters = {
  limit: number;
  dateFrom: string;
  dateTo: string;
};
