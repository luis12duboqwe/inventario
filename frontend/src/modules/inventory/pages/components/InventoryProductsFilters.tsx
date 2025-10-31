import { Search } from "lucide-react";

import TextField from "../../../../shared/components/ui/TextField";
import { useInventoryLayout } from "../context/InventoryLayoutContext";
import type { Device } from "../../../../api";

function InventoryProductsFilters() {
  const {
    module: { stores, selectedStoreId, setSelectedStoreId }, // [PACK30-31-FRONTEND]
    search: { inventoryQuery, setInventoryQuery, estadoFilter, setEstadoFilter },
  } = useInventoryLayout();

  return (
    <div className="inventory-toolbar">
      <label className="select-inline">{/* [PACK30-31-FRONTEND] */}
        <span>Sucursal</span>
        <select
          value={selectedStoreId ?? ""}
          onChange={(event) =>
            setSelectedStoreId(event.target.value ? Number(event.target.value) : null)
          }
        >
          {stores.length === 0 ? (
            <option value="">Sin sucursales</option>
          ) : (
            stores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))
          )}
        </select>
      </label>
      <TextField
        className="inventory-controls__search"
        type="search"
        label="Buscar por IMEI, modelo o SKU"
        hideLabel
        value={inventoryQuery}
        onChange={(event) => {
          setInventoryQuery(event.target.value);
        }}
        placeholder="Buscar por IMEI, modelo o SKU"
        leadingIcon={<Search size={16} aria-hidden="true" />}
        autoComplete="off"
      />
      <label className="select-inline">
        <span>Estado comercial</span>
        <select
          value={estadoFilter}
          onChange={(event) => setEstadoFilter(event.target.value as Device["estado_comercial"] | "TODOS")}
        >
          <option value="TODOS">Todos</option>
          <option value="nuevo">Nuevo</option>
          <option value="A">Grado A</option>
          <option value="B">Grado B</option>
          <option value="C">Grado C</option>
        </select>
      </label>
    </div>
  );
}

export default InventoryProductsFilters;
