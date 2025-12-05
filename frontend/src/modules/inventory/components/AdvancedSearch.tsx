import { useState } from "react";
import { useForm } from "react-hook-form";
import type { CatalogDevice, Device, DeviceSearchFilters } from "@api/inventory";
import { searchCatalogDevices } from "@api/inventory";
import { FILTER_ALL_VALUE, FILTER_ALL_LABEL } from "../../../config/constants";
import TextField from "@components/ui/TextField";
import Select from "@components/ui/Select";
import Button from "@components/ui/Button";
import Tooltip from "@components/ui/Tooltip";
import { HelpCircle, Search, Inbox } from "lucide-react";
import "./AdvancedSearch.css";

type Props = {
  token: string;
};

type AdvancedFiltersState = Omit<DeviceSearchFilters, "estado_comercial"> & {
  estado_comercial?: NonNullable<Device["estado_comercial"]> | typeof FILTER_ALL_VALUE;
};

const createInitialFilters = (): AdvancedFiltersState => ({
  imei: "",
  serial: "",
  color: "",
  marca: "",
  modelo: "",
  categoria: "",
  condicion: "",
  estado_comercial: FILTER_ALL_VALUE,
  estado: "",
  ubicacion: "",
  proveedor: "",
  fecha_ingreso_desde: "",
  fecha_ingreso_hasta: "",
});

function AdvancedSearch({ token }: Props) {
  const [results, setResults] = useState<CatalogDevice[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const { register, handleSubmit, reset } = useForm<AdvancedFiltersState>({
    defaultValues: createInitialFilters(),
  });

  const onSubmit = async (data: AdvancedFiltersState) => {
    const payload: DeviceSearchFilters = {};

    if (data.imei?.trim()) payload.imei = data.imei.trim();
    if (data.serial?.trim()) payload.serial = data.serial.trim();
    if (data.color?.trim()) payload.color = data.color.trim();
    if (data.marca?.trim()) payload.marca = data.marca.trim();
    if (data.modelo?.trim()) payload.modelo = data.modelo.trim();
    if (data.categoria?.trim()) payload.categoria = data.categoria.trim();
    if (data.condicion?.trim()) payload.condicion = data.condicion.trim();

    if (data.estado_comercial && data.estado_comercial !== FILTER_ALL_VALUE) {
      payload.estado_comercial = data.estado_comercial as Device["estado_comercial"];
    }

    if (data.estado?.trim()) payload.estado = data.estado.trim();
    if (data.ubicacion?.trim()) payload.ubicacion = data.ubicacion.trim();
    if (data.proveedor?.trim()) payload.proveedor = data.proveedor.trim();

    // Handle capacidad_gb specifically
    if (
      data.capacidad_gb !== undefined &&
      data.capacidad_gb !== null &&
      data.capacidad_gb.toString() !== ""
    ) {
      const cap = Number(data.capacidad_gb);
      if (!isNaN(cap)) {
        payload.capacidad_gb = cap;
      }
    }

    if (data.fecha_ingreso_desde) payload.fecha_ingreso_desde = data.fecha_ingreso_desde;
    if (data.fecha_ingreso_hasta) payload.fecha_ingreso_hasta = data.fecha_ingreso_hasta;

    if (Object.keys(payload).length === 0) {
      setError("Ingresa al menos un criterio de búsqueda");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const response = await searchCatalogDevices(token, payload);
      setResults(response);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible consultar el catálogo");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    reset(createInitialFilters());
    setResults([]);
    setError(null);
    setSearched(false);
  };

  return (
    <section className="card catalog-card fade-in">
      <header className="card-header">
        <h2 className="accent-title">Búsqueda avanzada de dispositivos</h2>
        <p className="card-subtitle">
          IMEI y serie únicos, coincidencias por marca, modelo, color y capacidad.
        </p>
      </header>
      <form className="catalog-form" onSubmit={handleSubmit(onSubmit)}>
        <div className="form-grid">
          <TextField
            label="IMEI"
            maxLength={18}
            placeholder="Hasta 18 dígitos"
            {...register("imei")}
            trailingIcon={
              <Tooltip content="Identificador único internacional (15-17 dígitos)">
                <HelpCircle size={16} className="text-muted cursor-help" />
              </Tooltip>
            }
          />
          <TextField
            label="Serie"
            maxLength={120}
            placeholder="Número de serie"
            {...register("serial")}
            trailingIcon={
              <Tooltip content="Número de serie del fabricante">
                <HelpCircle size={16} className="text-muted cursor-help" />
              </Tooltip>
            }
          />
          <TextField label="Capacidad (GB)" type="number" min={0} {...register("capacidad_gb")} />
          <TextField label="Marca" maxLength={80} {...register("marca")} />
          <TextField label="Modelo" maxLength={120} {...register("modelo")} />
          <TextField label="Color" maxLength={60} {...register("color")} />
          <TextField label="Categoría" maxLength={80} {...register("categoria")} />
          <TextField label="Condición" maxLength={60} {...register("condicion")} />
          <Select label="Estado comercial" {...register("estado_comercial")}>
            <option value={FILTER_ALL_VALUE}>{FILTER_ALL_LABEL}</option>
            <option value="nuevo">Nuevo</option>
            <option value="A">Grado A</option>
            <option value="B">Grado B</option>
            <option value="C">Grado C</option>
          </Select>
          <TextField label="Estado inventario" maxLength={40} {...register("estado")} />
          <TextField label="Ubicación" maxLength={120} {...register("ubicacion")} />
          <TextField label="Proveedor" maxLength={120} {...register("proveedor")} />
          <TextField label="Fecha ingreso desde" type="date" {...register("fecha_ingreso_desde")} />
          <TextField label="Fecha ingreso hasta" type="date" {...register("fecha_ingreso_hasta")} />
        </div>
        <div className="form-actions">
          <Button type="submit" disabled={loading}>
            {loading ? "Buscando…" : "Buscar"}
          </Button>
          <Button variant="ghost" type="button" onClick={handleReset} disabled={loading}>
            Limpiar
          </Button>
        </div>
      </form>
      {error && <p className="error-text">{error}</p>}
      {results.length > 0 ? (
        <div className="table-wrapper">
          <table className="scrollable-table">
            <thead>
              <tr>
                <th>Sucursal</th>
                <th>SKU</th>
                <th>Marca</th>
                <th>Modelo</th>
                <th>Categoría</th>
                <th>Condición</th>
                <th>Color</th>
                <th>Capacidad</th>
                <th>IMEI</th>
                <th>Serie</th>
                <th>Estado</th>
                <th>Estado inventario</th>
                <th>Ubicación</th>
                <th>Ingreso</th>
              </tr>
            </thead>
            <tbody>
              {results.map((device) => (
                <tr key={`${device.id}-${device.store_id}`}>
                  <td data-label="Sucursal">{device.store_name}</td>
                  <td data-label="SKU">{device.sku}</td>
                  <td data-label="Marca">{device.marca ?? "—"}</td>
                  <td data-label="Modelo">{device.modelo ?? "—"}</td>
                  <td data-label="Categoría">{device.categoria ?? "—"}</td>
                  <td data-label="Condición">{device.condicion ?? "—"}</td>
                  <td data-label="Color">{device.color ?? "—"}</td>
                  <td data-label="Capacidad">{device.capacidad ?? device.capacidad_gb ?? "—"}</td>
                  <td data-label="IMEI">{device.imei ?? "—"}</td>
                  <td data-label="Serie">{device.serial ?? "—"}</td>
                  <td data-label="Estado">{device.estado_comercial ?? "—"}</td>
                  <td data-label="Estado inventario">{device.estado ?? "—"}</td>
                  <td data-label="Ubicación">{device.ubicacion ?? "—"}</td>
                  <td data-label="Ingreso">{device.fecha_ingreso ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : searched ? (
        <div className="empty-state">
          <Inbox size={48} className="text-muted mb-2" />
          <p className="muted-text">Sin resultados. Ajusta los filtros y vuelve a intentarlo.</p>
        </div>
      ) : (
        <div className="empty-state">
          <Search size={48} className="text-muted mb-2" />
          <p className="muted-text">Completa los criterios para iniciar la búsqueda corporativa.</p>
        </div>
      )}
    </section>
  );
}

export default AdvancedSearch;
