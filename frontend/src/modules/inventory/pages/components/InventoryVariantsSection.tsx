import { FormEvent, useMemo, useState } from "react";

import { useInventoryLayout } from "../context/InventoryLayoutContext";
import { promptCorporateReason } from "../../utils/corporateReason";

type VariantFormState = {
  editingId: number | null;
  deviceId: string;
  name: string;
  sku: string;
  barcode: string;
  priceOverride: string;
  isDefault: boolean;
  isActive: boolean;
};

const INITIAL_VARIANT_FORM: VariantFormState = {
  editingId: null,
  deviceId: "",
  name: "",
  sku: "",
  barcode: "",
  priceOverride: "",
  isDefault: false,
  isActive: true,
};

function InventoryVariantsSection(): JSX.Element | null {
  const {
    module: { devices, selectedStoreId, enableVariants, formatCurrency },
    variants,
  } = useInventoryLayout();
  const [formState, setFormState] = useState<VariantFormState>(INITIAL_VARIANT_FORM);

  const availableDevices = useMemo(() => {
    if (selectedStoreId == null) {
      return devices;
    }
    return devices.filter((device) => device.store_id === selectedStoreId);
  }, [devices, selectedStoreId]);

  if (!enableVariants) {
    return null;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.deviceId) {
      return;
    }
    const reason = promptCorporateReason(
      formState.editingId ? "Actualizar variante" : "Registrar nueva variante",
    );
    if (!reason) {
      return;
    }
    const priceOverrideInput = formState.priceOverride.trim();
    const parsedPrice =
      priceOverrideInput === "" ? undefined : Number.parseFloat(priceOverrideInput);
    const payload = {
      name: formState.name.trim(),
      variant_sku: formState.sku.trim(),
      barcode: formState.barcode.trim() || undefined,
      unit_price_override:
        parsedPrice !== undefined && !Number.isNaN(parsedPrice) ? parsedPrice : undefined,
      is_default: formState.isDefault,
      is_active: formState.isActive,
    };
    if (formState.editingId) {
      await variants.update(formState.editingId, payload, reason);
    } else {
      await variants.create(Number(formState.deviceId), payload, reason);
    }
    setFormState((state) => ({ ...INITIAL_VARIANT_FORM, deviceId: state.deviceId }));
  };

  const handleEdit = (variantId: number) => {
    const variant = variants.items.find((entry) => entry.id === variantId);
    if (!variant) {
      return;
    }
    setFormState({
      editingId: variant.id,
      deviceId: String(variant.device_id),
      name: variant.name,
      sku: variant.variant_sku,
      barcode: variant.barcode ?? "",
      priceOverride: variant.unit_price_override?.toString() ?? "",
      isDefault: variant.is_default,
      isActive: variant.is_active,
    });
  };

  const handleArchive = async (variantId: number) => {
    const reason = promptCorporateReason("Archivar variante del inventario");
    if (!reason) {
      return;
    }
    await variants.archive(variantId, reason);
    if (formState.editingId === variantId) {
      setFormState(INITIAL_VARIANT_FORM);
    }
  };

  return (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>Variantes de producto</h2>
          <p className="card-subtitle">
            Gestiona atributos específicos para cada dispositivo y controla sus precios
            individuales.
          </p>
        </div>
        <div className="card-actions">
          <label className="toggle">
            <input
              type="checkbox"
              checked={variants.includeInactive}
              onChange={(event) => variants.setIncludeInactive(event.target.checked)}
            />
            Mostrar inactivas
          </label>
        </div>
      </header>

      <div className="table-responsive">
        {variants.loading ? (
          <p className="muted-text">Cargando variantes…</p>
        ) : variants.items.length === 0 ? (
          <p className="muted-text">No se registran variantes para los filtros actuales.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Nombre</th>
                <th>Dispositivo</th>
                <th>Precio específico</th>
                <th>Predeterminada</th>
                <th>Estado</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {variants.items.map((variant) => (
                <tr key={variant.id}>
                  <td>{variant.variant_sku}</td>
                  <td>{variant.name}</td>
                  <td>{variant.device_name}</td>
                  <td>
                    {variant.unit_price_override != null
                      ? formatCurrency(variant.unit_price_override)
                      : "—"}
                  </td>
                  <td>{variant.is_default ? "Sí" : "No"}</td>
                  <td>{variant.is_active ? "Activo" : "Archivado"}</td>
                  <td className="table-actions">
                    <button type="button" onClick={() => handleEdit(variant.id)}>
                      Editar
                    </button>
                    <button type="button" onClick={() => handleArchive(variant.id)}>
                      Archivar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <form className="card form-grid" onSubmit={handleSubmit}>
        <h3>{formState.editingId ? "Editar variante" : "Registrar variante"}</h3>
        <div className="form-row">
          <label htmlFor="variant-device">Dispositivo base</label>
          <select
            id="variant-device"
            value={formState.deviceId}
            onChange={(event) =>
              setFormState((state) => ({ ...state, deviceId: event.target.value }))
            }
            required
          >
            <option value="">Selecciona un dispositivo</option>
            {availableDevices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.sku} · {device.name}
              </option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label htmlFor="variant-name">Nombre</label>
          <input
            id="variant-name"
            type="text"
            value={formState.name}
            onChange={(event) => setFormState((state) => ({ ...state, name: event.target.value }))}
            required
          />
        </div>
        <div className="form-row">
          <label htmlFor="variant-sku">SKU de variante</label>
          <input
            id="variant-sku"
            type="text"
            value={formState.sku}
            onChange={(event) => setFormState((state) => ({ ...state, sku: event.target.value }))}
            required
          />
        </div>
        <div className="form-row">
          <label htmlFor="variant-barcode">Código de barras</label>
          <input
            id="variant-barcode"
            type="text"
            value={formState.barcode}
            onChange={(event) =>
              setFormState((state) => ({ ...state, barcode: event.target.value }))
            }
          />
        </div>
        <div className="form-row">
          <label htmlFor="variant-price">Precio específico</label>
          <input
            id="variant-price"
            type="number"
            step="0.01"
            min="0"
            value={formState.priceOverride}
            onChange={(event) =>
              setFormState((state) => ({ ...state, priceOverride: event.target.value }))
            }
            placeholder="Usa el precio del dispositivo por defecto"
          />
        </div>
        <div className="form-row inline">
          <label>
            <input
              type="checkbox"
              checked={formState.isDefault}
              onChange={(event) =>
                setFormState((state) => ({ ...state, isDefault: event.target.checked }))
              }
            />
            Marcar como variante predeterminada
          </label>
          <label>
            <input
              type="checkbox"
              checked={formState.isActive}
              onChange={(event) =>
                setFormState((state) => ({ ...state, isActive: event.target.checked }))
              }
            />
            Activa
          </label>
        </div>
        <div className="form-actions">
          <button type="submit" className="primary">
            {formState.editingId ? "Actualizar variante" : "Crear variante"}
          </button>
          {formState.editingId ? (
            <button
              type="button"
              onClick={() => setFormState(INITIAL_VARIANT_FORM)}
              className="secondary"
            >
              Cancelar
            </button>
          ) : null}
        </div>
      </form>
    </section>
  );
}

export default InventoryVariantsSection;
