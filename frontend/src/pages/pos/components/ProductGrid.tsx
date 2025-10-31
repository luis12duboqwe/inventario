import type { Device } from "../../../api";

type Props = {
  quickDevices: Device[];
  filteredDevices: Device[];
  disabled: boolean;
  onDeviceSelect: (device: Device) => void;
};

function ProductGrid({ quickDevices, filteredDevices, disabled, onDeviceSelect }: Props) {
  return (
    <>
      {quickDevices.length > 0 ? (
        <div className="quick-actions">
          <span className="muted-text">Venta rápida:</span>
          {quickDevices.map((device) => (
            <button
              type="button"
              key={device.id}
              className="btn btn--ghost"
              onClick={() => onDeviceSelect(device)}
              disabled={disabled}
            >
              {device.sku}
            </button>
          ))}
        </div>
      ) : null}
      <div className="quick-actions">
        {filteredDevices.map((device) => (
          <button
            type="button"
            key={device.id}
            className="btn btn--secondary"
            onClick={() => onDeviceSelect(device)}
            disabled={disabled}
          >
            {device.sku} · {device.name}
          </button>
        ))}
      </div>
    </>
  );
}

export default ProductGrid;
