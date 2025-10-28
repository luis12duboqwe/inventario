import type { FormEvent } from "react";
import type {
  PurchaseVendor,
  PurchaseVendorHistory,
} from "../../../../api";
import type {
  VendorFilters,
  VendorForm,
  VendorHistoryFilters,
} from "../../../../types/purchases";

type PurchasesSidePanelProps = {
  vendorForm: VendorForm;
  vendorFiltersDraft: VendorFilters;
  vendorHistoryFiltersDraft: VendorHistoryFilters;
  vendors: PurchaseVendor[];
  selectedVendor: PurchaseVendor | null;
  vendorHistory: PurchaseVendorHistory | null;
  vendorSaving: boolean;
  vendorExporting: boolean;
  vendorsLoading: boolean;
  vendorHistoryLoading: boolean;
  editingVendorId: number | null;
  currencyFormatter: Intl.NumberFormat;
  onVendorFormSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onVendorInputChange: (field: keyof VendorForm, value: string) => void;
  onVendorFormCancel: () => void;
  onVendorFiltersSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onVendorFiltersReset: () => void;
  onVendorFiltersChange: <Field extends keyof VendorFilters>(
    field: Field,
    value: VendorFilters[Field],
  ) => void;
  onVendorExport: () => void;
  onVendorEdit: (vendor: PurchaseVendor) => void;
  onVendorSelect: (vendorId: number) => void;
  onVendorToggleStatus: (vendor: PurchaseVendor) => void;
  onVendorHistoryFiltersSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onVendorHistoryFiltersReset: () => void;
  onVendorHistoryFiltersChange: <Field extends keyof VendorHistoryFilters>(
    field: Field,
    value: VendorHistoryFilters[Field],
  ) => void;
};

const PurchasesSidePanel = ({
  vendorForm,
  vendorFiltersDraft,
  vendorHistoryFiltersDraft,
  vendors,
  selectedVendor,
  vendorHistory,
  vendorSaving,
  vendorExporting,
  vendorsLoading,
  vendorHistoryLoading,
  editingVendorId,
  currencyFormatter,
  onVendorFormSubmit,
  onVendorInputChange,
  onVendorFormCancel,
  onVendorFiltersSubmit,
  onVendorFiltersReset,
  onVendorFiltersChange,
  onVendorExport,
  onVendorEdit,
  onVendorSelect,
  onVendorToggleStatus,
  onVendorHistoryFiltersSubmit,
  onVendorHistoryFiltersReset,
  onVendorHistoryFiltersChange,
}: PurchasesSidePanelProps) => {
  return (
    <section className="card">
      <h2>Gestión de proveedores</h2>
      <p className="card-subtitle">
        Registra proveedores, consulta su historial y actualiza su estado sin perder el contexto corporativo.
      </p>
      <div className="section-grid">
        <form className="form-grid" onSubmit={onVendorFormSubmit}>
          <h3 className="form-span">Registro/edición</h3>
          <label>
            Nombre
            <input
              value={vendorForm.nombre}
              onChange={(event) => onVendorInputChange("nombre", event.target.value)}
              placeholder="Proveedor corporativo"
              required
            />
          </label>
          <label>
            Teléfono
            <input
              value={vendorForm.telefono}
              onChange={(event) => onVendorInputChange("telefono", event.target.value)}
              placeholder="Opcional"
            />
          </label>
          <label>
            Correo
            <input
              type="email"
              value={vendorForm.correo}
              onChange={(event) => onVendorInputChange("correo", event.target.value)}
              placeholder="Opcional"
            />
          </label>
          <label>
            Dirección
            <input
              value={vendorForm.direccion}
              onChange={(event) => onVendorInputChange("direccion", event.target.value)}
              placeholder="Opcional"
            />
          </label>
          <label>
            Tipo
            <input
              value={vendorForm.tipo}
              onChange={(event) => onVendorInputChange("tipo", event.target.value)}
              placeholder="Ej. Mayorista"
            />
          </label>
          <label className="form-span">
            Notas
            <textarea
              value={vendorForm.notas}
              onChange={(event) => onVendorInputChange("notas", event.target.value)}
              rows={3}
            />
          </label>
          <div className="form-actions form-span">
            <button type="submit" className="btn btn--primary" disabled={vendorSaving}>
              {vendorSaving
                ? "Guardando…"
                : editingVendorId
                ? "Actualizar proveedor"
                : "Registrar proveedor"}
            </button>
            {editingVendorId ? (
              <button type="button" className="btn btn--ghost" onClick={onVendorFormCancel}>
                Cancelar edición
              </button>
            ) : null}
          </div>
        </form>

        <form className="form-grid" onSubmit={onVendorFiltersSubmit}>
          <h3 className="form-span">Filtros</h3>
          <label>
            Búsqueda
            <input
              value={vendorFiltersDraft.query}
              onChange={(event) => onVendorFiltersChange("query", event.target.value)}
              placeholder="Nombre, correo o notas"
            />
          </label>
          <label>
            Estado
            <select
              value={vendorFiltersDraft.status}
              onChange={(event) => onVendorFiltersChange("status", event.target.value)}
            >
              <option value="">Todos</option>
              <option value="activo">Activos</option>
              <option value="inactivo">Inactivos</option>
            </select>
          </label>
          <div className="form-actions">
            <button type="submit" className="btn btn--primary">
              Aplicar filtros
            </button>
            <button type="button" className="btn btn--ghost" onClick={onVendorFiltersReset}>
              Limpiar
            </button>
          </div>
          <button
            type="button"
            className="btn btn--secondary form-span"
            onClick={onVendorExport}
            disabled={vendorExporting}
          >
            {vendorExporting ? "Exportando…" : "Exportar proveedores CSV"}
          </button>
        </form>
      </div>

      {vendorsLoading ? <p className="muted-text">Cargando proveedores…</p> : null}
      {!vendorsLoading && vendors.length === 0 ? (
        <p className="muted-text">No se encontraron proveedores con los filtros actuales.</p>
      ) : null}

      {!vendorsLoading && vendors.length > 0 ? (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Proveedor</th>
                <th>Estado</th>
                <th>Total compras</th>
                <th>Impuesto</th>
                <th>Registros</th>
                <th>Última compra</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {vendors.map((vendor) => (
                <tr key={vendor.id_proveedor}>
                  <td>
                    <strong>{vendor.nombre}</strong>
                    <br />
                    <small className="muted-text">
                      {vendor.correo ? `${vendor.correo} · ` : ""}
                      {vendor.telefono || "Sin teléfono"}
                    </small>
                  </td>
                  <td>
                    <span className={`badge ${vendor.estado === "activo" ? "success" : "neutral"}`}>
                      {vendor.estado.toUpperCase()}
                    </span>
                  </td>
                  <td>{currencyFormatter.format(vendor.total_compras)}</td>
                  <td>{currencyFormatter.format(vendor.total_impuesto)}</td>
                  <td>{vendor.compras_registradas}</td>
                  <td>
                    {vendor.ultima_compra
                      ? new Date(vendor.ultima_compra).toLocaleString("es-MX")
                      : "—"}
                  </td>
                  <td>
                    <div className="transfer-actions">
                      <button
                        type="button"
                        className="btn btn--ghost"
                        onClick={() => onVendorSelect(vendor.id_proveedor)}
                      >
                        Ver historial
                      </button>
                      <button
                        type="button"
                        className="btn btn--ghost"
                        onClick={() => onVendorEdit(vendor)}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className="btn btn--ghost"
                        onClick={() => onVendorToggleStatus(vendor)}
                      >
                        {vendor.estado === "activo" ? "Desactivar" : "Reactivar"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <div className="section-divider">
        <h3>Detalle e historial del proveedor</h3>
        {!selectedVendor ? (
          <p className="muted-text">Selecciona un proveedor para consultar su historial.</p>
        ) : (
          <div className="section-grid">
            <div className="totals-card">
              <h4>{selectedVendor.nombre}</h4>
              <p className="muted-text">
                {selectedVendor.tipo ? `${selectedVendor.tipo} · ` : ""}
                {selectedVendor.estado === "activo" ? "Activo" : "Inactivo"}
              </p>
              {selectedVendor.direccion ? <p>{selectedVendor.direccion}</p> : null}
              {selectedVendor.notas ? <p className="muted-text">{selectedVendor.notas}</p> : null}
              <p>
                Compras registradas: <strong>{selectedVendor.compras_registradas}</strong>
              </p>
              <p>Total: {currencyFormatter.format(selectedVendor.total_compras)}</p>
              <p>Impuestos: {currencyFormatter.format(selectedVendor.total_impuesto)}</p>
            </div>

            <form className="form-grid" onSubmit={onVendorHistoryFiltersSubmit}>
              <h4 className="form-span">Filtrar historial</h4>
              <label>
                Desde
                <input
                  type="date"
                  value={vendorHistoryFiltersDraft.dateFrom}
                  onChange={(event) =>
                    onVendorHistoryFiltersChange("dateFrom", event.target.value)
                  }
                />
              </label>
              <label>
                Hasta
                <input
                  type="date"
                  value={vendorHistoryFiltersDraft.dateTo}
                  onChange={(event) =>
                    onVendorHistoryFiltersChange("dateTo", event.target.value)
                  }
                />
              </label>
              <label>
                Límite
                <input
                  type="number"
                  min={1}
                  max={200}
                  value={vendorHistoryFiltersDraft.limit}
                  onChange={(event) =>
                    onVendorHistoryFiltersChange(
                      "limit",
                      Number(event.target.value) || vendorHistoryFiltersDraft.limit,
                    )
                  }
                />
              </label>
              <div className="form-actions">
                <button type="submit" className="btn btn--primary">
                  Aplicar
                </button>
                <button type="button" className="btn btn--ghost" onClick={onVendorHistoryFiltersReset}>
                  Limpiar
                </button>
              </div>
            </form>
          </div>
        )}

        {vendorHistoryLoading ? (
          <p className="muted-text">Cargando historial…</p>
        ) : vendorHistory && vendorHistory.compras.length > 0 ? (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Fecha</th>
                  <th>Total</th>
                  <th>Impuestos</th>
                  <th>Usuario</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {vendorHistory.compras.map((purchase) => (
                  <tr key={purchase.id_compra}>
                    <td>#{purchase.id_compra}</td>
                    <td>{new Date(purchase.fecha).toLocaleString("es-MX")}</td>
                    <td>{currencyFormatter.format(purchase.total)}</td>
                    <td>{currencyFormatter.format(purchase.impuesto)}</td>
                    <td>{purchase.usuario_nombre || "—"}</td>
                    <td>{purchase.estado}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : vendorHistoryLoading ? null : vendorHistory ? (
          <p className="muted-text">Sin compras registradas en el rango indicado.</p>
        ) : null}

        {!vendorHistoryLoading && vendorHistory ? (
          <p className="muted-text">
            Total en el rango: {currencyFormatter.format(vendorHistory.total)} · Impuestos: {" "}
            {currencyFormatter.format(vendorHistory.impuesto)} · Registros analizados: {vendorHistory.registros}
          </p>
        ) : null}
      </div>
    </section>
  );
};

export default PurchasesSidePanel;
