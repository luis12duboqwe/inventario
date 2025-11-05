import { useState } from "react";
import type { Device, PosConfig, PosConfigUpdateInput } from "../../../../api";

type Props = {
  config: PosConfig | null;
  devices: Device[];
  onSave: (payload: PosConfigUpdateInput) => Promise<void>;
  loading: boolean;
};

function POSSettings({ config, devices, onSave, loading }: Props) {
  // Evitar setState en efectos: remonte del formulario cuando cambia la sucursal (config.store_id)
  if (!config) {
    return (
      <section className="card">
        <h3>Configuración POS</h3>
        <p className="muted-text">Selecciona una sucursal para personalizar impuestos y accesos rápidos.</p>
      </section>
    );
  }

  return (
    <POSSettingsForm
      key={config.store_id}
      config={config as PosConfig}
      devices={devices}
      onSave={onSave}
      loading={loading}
    />
  );
}

type POSSettingsFormProps = {
  config: PosConfig;
  devices: Device[];
  onSave: (payload: PosConfigUpdateInput) => Promise<void>;
  loading: boolean;
};

function POSSettingsForm({ config, devices, onSave, loading }: POSSettingsFormProps) {
  const [taxRate, setTaxRate] = useState<number>(() => config.tax_rate);
  const [invoicePrefix, setInvoicePrefix] = useState<string>(() => config.invoice_prefix);
  const [printerName, setPrinterName] = useState<string>(() => config.printer_name ?? "");
  const [printerProfile, setPrinterProfile] = useState<string>(() => config.printer_profile ?? "");
  const [quickProducts, setQuickProducts] = useState<number[]>(() => config.quick_product_ids);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!config) {
      return;
    }
    try {
      setError(null);
      setMessage(null);
      await onSave({
        store_id: config.store_id,
        tax_rate: Math.min(100, Math.max(0, taxRate)),
        invoice_prefix: invoicePrefix.trim().toUpperCase() || "POS",
        printer_name: printerName.trim() || undefined,
        printer_profile: printerProfile.trim() || undefined,
        quick_product_ids: quickProducts,
      });
      setMessage("Configuración guardada correctamente.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible actualizar la configuración POS.");
    }
  };

  return (
    <section className="card">
      <h3>Configuración POS</h3>
      <p className="card-subtitle">Define impuestos, prefijo de factura y accesos directos del mostrador.</p>
      {message ? <div className="alert success">{message}</div> : null}
      {error ? <div className="alert error">{error}</div> : null}
      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          Impuesto (%)
          <input
            type="number"
            min={0}
            max={100}
            value={taxRate}
            onChange={(event) => setTaxRate(Math.min(100, Math.max(0, Number(event.target.value))))}
          />
        </label>
        <label>
          Prefijo de factura
          <input value={invoicePrefix} onChange={(event) => setInvoicePrefix(event.target.value)} maxLength={12} />
        </label>
        <label>
          Impresora (opcional)
          <input value={printerName} onChange={(event) => setPrinterName(event.target.value)} />
        </label>
        <label>
          Perfil impresora (opcional)
          <input value={printerProfile} onChange={(event) => setPrinterProfile(event.target.value)} />
        </label>
        <label className="wide">
          Accesos rápidos
          <select
            multiple
            value={quickProducts.map(String)}
            onChange={(event) => {
              const options = Array.from(event.target.selectedOptions).map((option) => Number(option.value));
              setQuickProducts(options);
            }}
          >
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                #{device.id} · {device.sku} · {device.name}
              </option>
            ))}
          </select>
          <span className="muted-text">Los productos seleccionados aparecerán como botones de venta rápida.</span>
        </label>
        <div className="actions-row">
          <button type="submit" className="btn btn--primary" disabled={loading}>
            {loading ? "Guardando..." : "Guardar cambios"}
          </button>
        </div>
      </form>
      <p className="muted-text">Última actualización: {new Date(config.updated_at).toLocaleString("es-MX")}</p>
    </section>
  );
}

export default POSSettings;
