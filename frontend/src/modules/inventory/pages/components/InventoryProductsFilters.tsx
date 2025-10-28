import { Search } from "lucide-react";

import TextField from "../../../../shared/components/ui/TextField";
import { useInventoryLayout } from "../context/InventoryLayoutContext";
import type { Device } from "../../../../api";

function InventoryProductsFilters() {
  const {
    search: { inventoryQuery, setInventoryQuery, estadoFilter, setEstadoFilter },
  } = useInventoryLayout();

  return (
    <div className="inventory-toolbar">
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
