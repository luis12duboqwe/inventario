import type { FormEvent, RefObject } from "react";
import type { Customer, Device, Sale, Store } from "../../../../api";
import type { SaleFormState, SaleLine, SaleSummary } from "./types";
import { SaleForm } from "./SaleForm";
import { DeviceSearch } from "./DeviceSearch";
import { SaleCart } from "./SaleCart";
import { SaleTotals } from "./SaleTotals";

type Props = {
  stores: Store[];
  customers: Customer[];
  saleForm: SaleFormState;
  onSaleFormChange: (changes: Partial<SaleFormState>) => void;
  deviceQuery: string;
  onDeviceQueryChange: (value: string) => void;
  devices: Device[];
  isLoadingDevices: boolean;
  onAddDevice: (device: Device) => void;
  saleItems: SaleLine[];
  onQuantityChange: (deviceId: number, quantity: number) => void;
  onBatchCodeChange: (deviceId: number, batchCode: string) => void;
  onRemoveLine: (deviceId: number) => void;
  saleSummary: SaleSummary;
  paymentLabels: Record<Sale["payment_method"], string>;
  isSaving: boolean;
  isPrinting: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onReset: () => void;
  onRequestInvoice: () => void;
  formatCurrency: (value: number) => string;
  invoiceAvailable: boolean;
  deviceSearchRef?: RefObject<HTMLInputElement>;
  customerSelectRef?: RefObject<HTMLSelectElement>;
};

function SidePanel({
  stores,
  customers,
  saleForm,
  onSaleFormChange,
  deviceQuery,
  onDeviceQueryChange,
  devices,
  isLoadingDevices,
  onAddDevice,
  saleItems,
  onQuantityChange,
  onBatchCodeChange,
  onRemoveLine,
  saleSummary,
  paymentLabels,
  isSaving,
  isPrinting,
  onSubmit,
  onReset,
  onRequestInvoice,
  formatCurrency,
  invoiceAvailable,
  deviceSearchRef,
  customerSelectRef,
}: Props) {
  const deviceSearchDisabled = !saleForm.storeId;

  return (
    <form className="sales-form" onSubmit={onSubmit}>
      <SaleForm
        stores={stores}
        customers={customers}
        saleForm={saleForm}
        onSaleFormChange={onSaleFormChange}
        paymentLabels={paymentLabels}
        customerSelectRef={customerSelectRef}
      />

      <DeviceSearch
        deviceQuery={deviceQuery}
        onDeviceQueryChange={onDeviceQueryChange}
        devices={devices}
        isLoadingDevices={isLoadingDevices}
        onAddDevice={onAddDevice}
        disabled={deviceSearchDisabled}
        formatCurrency={formatCurrency}
        inputRef={deviceSearchRef}
      />

      <SaleCart
        saleItems={saleItems}
        onQuantityChange={onQuantityChange}
        onBatchCodeChange={onBatchCodeChange}
        onRemoveLine={onRemoveLine}
        formatCurrency={formatCurrency}
      />

      <SaleTotals
        saleSummary={saleSummary}
        isSaving={isSaving}
        isPrinting={isPrinting}
        invoiceAvailable={invoiceAvailable}
        onRequestInvoice={onRequestInvoice}
        onReset={onReset}
        formatCurrency={formatCurrency}
      />
    </form>
  );
}

export default SidePanel;
