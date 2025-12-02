import type { Device } from "../../../../api";

type Props = {
  deviceQuery: string;
  onDeviceQueryChange: (value: string) => void;
  devices: Device[];
  isLoadingDevices: boolean;
  onAddDevice: (device: Device) => void;
  disabled: boolean;
  formatCurrency: (value: number) => string;
};

export function DeviceSearch({
  deviceQuery,
  onDeviceQueryChange,
  devices,
  isLoadingDevices,
  onAddDevice,
  disabled,
  formatCurrency,
}: Props) {
  return (
    <>
      <div className="form-grid">
        <label className="span-2">
          Buscar dispositivo por IMEI, SKU o modelo
          <input
            value={deviceQuery}
            onChange={(event) => onDeviceQueryChange(event.target.value)}
            placeholder="Ej. 990000862471854 o FILTRO-1001"
            disabled={disabled}
          />
        </label>
      </div>

      <div className="section-divider">
        <h3>Dispositivos disponibles</h3>
        {disabled ? (
          <p className="muted-text">
            Selecciona una sucursal para consultar su inventario disponible.
          </p>
        ) : isLoadingDevices ? (
          <p className="muted-text">Cargando dispositivos disponibles...</p>
        ) : devices.length === 0 ? (
          <p className="muted-text">
            No se encontraron dispositivos disponibles con el criterio indicado.
          </p>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Modelo</th>
                  <th>Estado</th>
                  <th>Precio</th>
                  <th>Disponibles</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {devices.map((device) => (
                  <tr key={device.id}>
                    <td>{device.sku}</td>
                    <td>{device.name}</td>
                    <td>{device.condicion ?? device.estado ?? "—"}</td>
                    <td>{formatCurrency(device.unit_price)}</td>
                    <td>{device.quantity}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn--secondary"
                        onClick={() => onAddDevice(device)}
                        disabled={device.quantity === 0}
                      >
                        Agregar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
