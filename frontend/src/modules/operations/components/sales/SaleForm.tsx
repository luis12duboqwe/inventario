import type { Customer, Sale, Store } from "../../../../api";
import type { SaleFormState } from "./types";
import type { RefObject } from "react";

type Props = {
  stores: Store[];
  customers: Customer[];
  saleForm: SaleFormState;
  onSaleFormChange: (changes: Partial<SaleFormState>) => void;
  paymentLabels: Record<Sale["payment_method"], string>;
  customerSelectRef?: RefObject<HTMLSelectElement>;
};

export function SaleForm({
  stores,
  customers,
  saleForm,
  onSaleFormChange,
  paymentLabels,
  customerSelectRef,
}: Props) {
  return (
    <div className="form-grid">
      <label>
        Sucursal
        <select
          value={saleForm.storeId ?? ""}
          onChange={(event) =>
            onSaleFormChange({ storeId: event.target.value ? Number(event.target.value) : null })
          }
        >
          <option value="">Selecciona una sucursal</option>
          {stores.map((store) => (
            <option key={store.id} value={store.id}>
              {store.name}
            </option>
          ))}
        </select>
      </label>

      <label>
        Cliente registrado
        <select
          ref={customerSelectRef}
          value={saleForm.customerId ?? ""}
          onChange={(event) =>
            onSaleFormChange({
              customerId: event.target.value ? Number(event.target.value) : null,
              customerName: "",
            })
          }
        >
          <option value="">Venta de mostrador</option>
          {customers.map((customer) => (
            <option key={customer.id} value={customer.id}>
              {customer.name}
            </option>
          ))}
        </select>
      </label>

      <label>
        Cliente manual (opcional)
        <input
          value={saleForm.customerName}
          onChange={(event) =>
            onSaleFormChange({ customerName: event.target.value, customerId: null })
          }
          placeholder="Nombre del cliente"
        />
      </label>

      <label>
        Método de pago
        <select
          value={saleForm.paymentMethod}
          onChange={(event) =>
            onSaleFormChange({ paymentMethod: event.target.value as Sale["payment_method"] })
          }
        >
          {Object.entries(paymentLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>

      <label>
        Descuento (%)
        <input
          type="number"
          min={0}
          max={100}
          value={saleForm.discountPercent}
          onChange={(event) => onSaleFormChange({ discountPercent: Number(event.target.value) })}
        />
      </label>

      <label>
        Nota interna
        <input
          value={saleForm.notes}
          onChange={(event) => onSaleFormChange({ notes: event.target.value })}
          placeholder="Observaciones"
        />
      </label>

      <label>
        Motivo corporativo
        <input
          value={saleForm.reason}
          onChange={(event) => onSaleFormChange({ reason: event.target.value })}
          placeholder="Motivo para auditoría"
        />
      </label>
    </div>
  );
}
