import type { Store } from "../../../api";

type Props = {
  stores: Store[];
  selectedStoreId: number | null;
  onStoreChange: (storeId: number | null) => void;
  search: string;
  onSearchChange: (value: string) => void;
  searchDisabled: boolean;
};

function QuickSaleForm({
  stores,
  selectedStoreId,
  onStoreChange,
  search,
  onSearchChange,
  searchDisabled,
}: Props) {
  return (
    <div className="form-grid">
      <label>
        Sucursal
        <select
          value={selectedStoreId ?? ""}
          onChange={(event) => onStoreChange(event.target.value ? Number(event.target.value) : null)}
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
        Buscar producto
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="IMEI, nombre o modelo"
          disabled={searchDisabled}
        />
      </label>
    </div>
  );
}

export default QuickSaleForm;
