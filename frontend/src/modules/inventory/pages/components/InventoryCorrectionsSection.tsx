import Button from "../../../../shared/components/ui/Button";
import { useInventoryLayout } from "../context/InventoryLayoutContext";

function InventoryCorrectionsSection() {
  const {
    smartImport: { pendingDevices, pendingDevicesLoading, refreshPendingDevices },
    helpers: { resolvePendingFields, storeNameById },
    editing: { openEditDialog },
  } = useInventoryLayout();

  return (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>Correcciones pendientes</h2>
          <p className="card-subtitle">Completa los campos faltantes identificados por la importación inteligente.</p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => {
            void refreshPendingDevices();
          }}
          disabled={pendingDevicesLoading}
        >
          {pendingDevicesLoading ? "Actualizando…" : "Actualizar"}
        </Button>
      </header>
      {pendingDevicesLoading ? (
        <p className="muted-text">Cargando dispositivos pendientes…</p>
      ) : pendingDevices.length === 0 ? (
        <p className="muted-text">No hay dispositivos con información pendiente.</p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Dispositivo</th>
                <th>Sucursal</th>
                <th>Campos faltantes</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {pendingDevices.map((device) => {
                const missingFields = resolvePendingFields(device);
                const storeName = storeNameById.get(device.store_id) ?? `Sucursal nueva (ID ${device.store_id})`;
                return (
                  <tr key={device.id}>
                    <td>
                      <div className="pending-corrections__device">
                        <strong>{device.name}</strong>
                        <span className="muted-text">SKU {device.sku}</span>
                      </div>
                    </td>
                    <td>{storeName}</td>
                    <td>
                      {missingFields.length === 0 ? (
                        <span className="muted-text">Sin pendientes</span>
                      ) : (
                        <ul className="pending-corrections__missing">
                          {missingFields.map((field) => (
                            <li key={`${device.id}-${field}`}>{field}</li>
                          ))}
                        </ul>
                      )}
                    </td>
                    <td>
                      <span
                        className={`smart-import-status smart-import-status--${device.completo ? "ok" : "falta"}`}
                      >
                        {device.completo ? "Completo" : "Pendiente"}
                      </span>
                    </td>
                    <td>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => openEditDialog(device)}
                      >
                        Completar datos
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default InventoryCorrectionsSection;
