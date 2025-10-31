import React from "react";

import {
  ProductActivityTimeline,
  ProductAttributes,
  ProductHeader,
  ProductMediaGallery,
  ProductNotes,
  ProductPricingCard,
  ProductRelatedProducts,
  ProductStockPerStore,
  ProductVariantsTable,
} from "../components/product-detail";

type ProductDetail = {
  name?: string;
  sku?: string;
  status?: "ACTIVE" | "INACTIVE" | string;
  images?: Array<{ id: string; url: string }>;
  variants?: Array<{ id: string; sku: string; attrs: string; price: number; stock: number }>;
  events?: Array<{ id: string; date: string; message: string }>;
  note?: string;
  attributes?: Array<{ key: string; value: string }>;
  price?: number;
  cost?: number;
  margin?: number;
  stockByStore?: Array<{ store: string; qty: number }>;
  related?: Array<{ id: string; name: string }>;
};

export default function ProductDetailPage() {
  const product = React.useMemo<ProductDetail | null>(() => null, []);

  const handlePrint = React.useCallback(() => {
    console.info("Imprimir ficha de producto");
  }, []);

  const handleExportPDF = React.useCallback(() => {
    console.info("Exportar ficha en PDF");
  }, []);

  const handleOpenRelated = React.useCallback((id: string) => {
    console.info("Abrir producto relacionado", id);
  }, []);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <ProductHeader
        name={product?.name}
        sku={product?.sku}
        status={product?.status}
        onPrint={handlePrint}
        onExportPDF={handleExportPDF}
      />
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}>
        <div style={{ display: "grid", gap: 12 }}>
          <ProductMediaGallery images={product?.images} />
          <ProductVariantsTable items={product?.variants} />
          <ProductActivityTimeline items={product?.events} />
          <ProductNotes value={product?.note} />
        </div>
        <div style={{ display: "grid", gap: 12 }}>
          <ProductAttributes items={product?.attributes} />
          <ProductPricingCard base={product?.price ?? 0} cost={product?.cost ?? 0} margin={product?.margin ?? 0} />
          <ProductStockPerStore items={product?.stockByStore} />
          <ProductRelatedProducts items={product?.related} onOpen={handleOpenRelated} />
        </div>
      </div>
    </div>
  );
}
