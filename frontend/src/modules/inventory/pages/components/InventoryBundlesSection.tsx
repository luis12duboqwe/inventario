import { FormEvent, useMemo, useState } from "react";

import { useInventoryLayout } from "../context/InventoryLayoutContext";
import { promptCorporateReason } from "../../utils/corporateReason";

type BundleFormState = {
  editingId: number | null;
  storeId: string;
  name: string;
  sku: string;
  description: string;
  basePrice: string;
  isActive: boolean;
};

type BundleItemDraft = {
  key: number;
  deviceId: string;
  deviceLabel?: string | undefined;
  variantId: string;
  variantLabel?: string | undefined;
  quantity: string;
};

const createEmptyItem = (key: number): BundleItemDraft => ({
  key,
  deviceId: "",
  variantId: "",
  quantity: "1",
});

function InventoryBundlesSection(): JSX.Element | null {
  const {
    module: { devices, stores, selectedStoreId, enableBundles, enableVariants, formatCurrency },
    variants,
    bundles,
    helpers: { storeNameById },
  } = useInventoryLayout();

  const [formState, setFormState] = useState<BundleFormState>(() => ({
    editingId: null,
    storeId: selectedStoreId ? String(selectedStoreId) : "",
    name: "",
    sku: "",
    description: "",
    basePrice: "",
    isActive: true,
  }));
  const [itemDrafts, setItemDrafts] = useState<BundleItemDraft[]>([createEmptyItem(0)]);
  const [nextItemKey, setNextItemKey] = useState(1);

  if (!formState.editingId) {
    const newStoreId = selectedStoreId ? String(selectedStoreId) : "";
    if (formState.storeId !== newStoreId) {
      setFormState((state) => ({
        ...state,
        storeId: newStoreId,
      }));
    }
  }

  const resolvedStoreId = useMemo(() => {
    if (formState.storeId.trim() !== "") {
      const parsed = Number.parseInt(formState.storeId, 10);
      return Number.isNaN(parsed) ? undefined : parsed;
    }
    return selectedStoreId ?? undefined;
  }, [formState.storeId, selectedStoreId]);

  const availableDevices = useMemo(() => {
    if (resolvedStoreId == null) {
      return devices;
    }
    return devices.filter((device) => device.store_id === resolvedStoreId);
  }, [devices, resolvedStoreId]);

  const deviceOptions = useMemo(
    () =>
      availableDevices.map((device) => ({
        value: String(device.id),
        label: `${device.sku} · ${device.name}`,
      })),
    [availableDevices],
  );

  const resetForm = () => {
    setFormState({
      editingId: null,
      storeId: selectedStoreId ? String(selectedStoreId) : "",
      name: "",
      sku: "",
      description: "",
      basePrice: "",
      isActive: true,
    });
    setItemDrafts([createEmptyItem(0)]);
    setNextItemKey(1);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const preparedItems = itemDrafts
      .map((item) => {
        if (!item.deviceId) {
          return null;
        }
        const quantityValue = Number.parseInt(item.quantity, 10);
        const safeQuantity = Number.isNaN(quantityValue) || quantityValue <= 0 ? 1 : quantityValue;
        return {
          device_id: Number(item.deviceId),
          variant_id: item.variantId ? Number(item.variantId) : null,
          quantity: safeQuantity,
        };
      })
      .filter(
        (entry): entry is { device_id: number; variant_id: number | null; quantity: number } =>
          entry !== null,
      );

    if (preparedItems.length === 0) {
      window.alert("Agrega al menos un dispositivo al combo corporativo.");
      return;
    }

    const reason = promptCorporateReason(
      formState.editingId ? "Actualizar combo" : "Registrar nuevo combo",
    );
    if (!reason) {
      return;
    }

    const basePriceInput = formState.basePrice.trim();
    const parsedBasePrice =
      basePriceInput === "" ? null : Number.parseFloat(basePriceInput.replace(",", "."));
    const sanitizedBasePrice =
      parsedBasePrice !== null && !Number.isNaN(parsedBasePrice) ? parsedBasePrice : null;

    const storeIdValue =
      formState.storeId.trim() !== ""
        ? Number.parseInt(formState.storeId, 10)
        : selectedStoreId ?? undefined;
    const sanitizedStoreId =
      storeIdValue !== undefined && !Number.isNaN(storeIdValue) ? storeIdValue : null;

    const payloadBase = {
      store_id: sanitizedStoreId,
      name: formState.name.trim(),
      bundle_sku: formState.sku.trim(),
      description: formState.description.trim() || null,
      base_price: sanitizedBasePrice,
      is_active: formState.isActive,
    };

    if (formState.editingId) {
      await bundles.update(
        formState.editingId,
        {
          ...payloadBase,
          items: preparedItems,
        },
        reason,
      );
    } else {
      await bundles.create(
        {
          ...payloadBase,
          items: preparedItems,
        },
        reason,
      );
    }

    resetForm();
  };

  const handleEdit = (bundleId: number) => {
    const bundle = bundles.items.find((entry) => entry.id === bundleId);
    if (!bundle) {
      return;
    }
    setFormState({
      editingId: bundle.id,
      storeId: bundle.store_id ? String(bundle.store_id) : "",
      name: bundle.name,
      sku: bundle.bundle_sku,
      description: bundle.description ?? "",
      basePrice: bundle.base_price != null ? String(bundle.base_price) : "",
      isActive: bundle.is_active,
    });
    setItemDrafts(
      bundle.items.length > 0
        ? bundle.items.map((item, index) => ({
            key: index,
            deviceId: String(item.device_id),
            deviceLabel: `${item.device_sku} · ${item.device_name}`,
            variantId: item.variant_id ? String(item.variant_id) : "",
            variantLabel: item.variant_name ?? undefined,
            quantity: String(item.quantity ?? 1),
          }))
        : [createEmptyItem(0)],
    );
    setNextItemKey(bundle.items.length);
  };

  const handleArchive = async (bundleId: number) => {
    const reason = promptCorporateReason("Archivar combo del inventario");
    if (!reason) {
      return;
    }
    await bundles.archive(bundleId, reason);
    if (formState.editingId === bundleId) {
      resetForm();
    }
  };

  const handleAddItem = () => {
    setItemDrafts((current) => [...current, createEmptyItem(nextItemKey)]);
    setNextItemKey((value) => value + 1);
  };

  const handleRemoveItem = (key: number) => {
    setItemDrafts((current) => {
      const filtered = current.filter((item) => item.key !== key);
      if (filtered.length === 0) {
        return [createEmptyItem(0)];
      }
      return filtered;
    });
  };

  const handleItemDeviceChange = (key: number, deviceId: string) => {
    setItemDrafts((current) =>
      current.map((item) => {
        if (item.key !== key) {
          return item;
        }
        const numericDeviceId = Number.parseInt(deviceId, 10);
        const device = devices.find((entry) => entry.id === numericDeviceId);
        return {
          ...item,
          deviceId,
          deviceLabel: device ? `${device.sku} · ${device.name}` : item.deviceLabel,
          variantId: "",
          variantLabel: undefined,
        };
      }),
    );
  };

  const handleItemVariantChange = (key: number, variantId: string) => {
    setItemDrafts((current) =>
      current.map((item) => {
        if (item.key !== key) {
          return item;
        }
        const numericVariantId = Number.parseInt(variantId, 10);
        const variant = variants.items.find((entry) => entry.id === numericVariantId);
        return {
          ...item,
          variantId,
          variantLabel: variant ? variant.name : item.variantLabel,
        };
      }),
    );
  };

  const handleItemQuantityChange = (key: number, quantity: string) => {
    setItemDrafts((current) =>
      current.map((item) => (item.key === key ? { ...item, quantity } : item)),
    );
  };

  if (!enableBundles) {
    return null;
  }

  return (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>Combos y paquetes</h2>
          <p className="card-subtitle">
            Agrupa dispositivos compatibles para ventas rápidas y controla precios corporativos
            especiales.
          </p>
        </div>
        <div className="card-actions">
          <label className="toggle">
            <input
              type="checkbox"
              checked={bundles.includeInactive}
              onChange={(event) => bundles.setIncludeInactive(event.target.checked)}
            />
            Mostrar inactivos
          </label>
          <button type="button" className="secondary" onClick={resetForm}>
            Limpiar formulario
          </button>
        </div>
      </header>

      <div className="table-responsive">
        {bundles.loading ? (
          <p className="muted-text">Cargando combos configurados…</p>
        ) : bundles.items.length === 0 ? (
          <p className="muted-text">No se han configurado combos para los filtros actuales.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Nombre</th>
                <th>Sucursal</th>
                <th>Precio base</th>
                <th>Componentes</th>
                <th>Estado</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {bundles.items.map((bundle) => (
                <tr key={bundle.id}>
                  <td>{bundle.bundle_sku}</td>
                  <td>{bundle.name}</td>
                  <td>{bundle.store_id ? storeNameById.get(bundle.store_id) : "General"}</td>
                  <td>{formatCurrency(bundle.base_price)}</td>
                  <td>
                    <ul>
                      {bundle.items.map((item) => (
                        <li key={`${bundle.id}-${item.device_id}-${item.variant_id ?? "base"}`}>
                          {item.device_sku} · {item.device_name}
                          {item.variant_name ? ` (${item.variant_name})` : ""} × {item.quantity}
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td>{bundle.is_active ? "Activo" : "Archivado"}</td>
                  <td className="table-actions">
                    <button type="button" onClick={() => handleEdit(bundle.id)}>
                      Editar
                    </button>
                    <button type="button" onClick={() => handleArchive(bundle.id)}>
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
        <h3>{formState.editingId ? "Editar combo" : "Registrar combo"}</h3>
        <div className="form-row">
          <label htmlFor="bundle-store">Sucursal asignada</label>
          <select
            id="bundle-store"
            value={formState.storeId}
            onChange={(event) =>
              setFormState((state) => ({ ...state, storeId: event.target.value }))
            }
          >
            <option value="">Todas las sucursales</option>
            {stores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label htmlFor="bundle-name">Nombre</label>
          <input
            id="bundle-name"
            type="text"
            value={formState.name}
            onChange={(event) => setFormState((state) => ({ ...state, name: event.target.value }))}
            required
          />
        </div>
        <div className="form-row">
          <label htmlFor="bundle-sku">SKU del combo</label>
          <input
            id="bundle-sku"
            type="text"
            value={formState.sku}
            onChange={(event) => setFormState((state) => ({ ...state, sku: event.target.value }))}
            required
          />
        </div>
        <div className="form-row">
          <label htmlFor="bundle-description">Descripción</label>
          <textarea
            id="bundle-description"
            value={formState.description}
            onChange={(event) =>
              setFormState((state) => ({ ...state, description: event.target.value }))
            }
            rows={2}
          />
        </div>
        <div className="form-row">
          <label htmlFor="bundle-base-price">Precio base</label>
          <input
            id="bundle-base-price"
            type="number"
            step="0.01"
            min="0"
            value={formState.basePrice}
            onChange={(event) =>
              setFormState((state) => ({ ...state, basePrice: event.target.value }))
            }
            placeholder="Ej. 499.90"
          />
        </div>
        <div className="form-row inline">
          <label>
            <input
              type="checkbox"
              checked={formState.isActive}
              onChange={(event) =>
                setFormState((state) => ({ ...state, isActive: event.target.checked }))
              }
            />
            Activo
          </label>
        </div>

        <div className="form-row full">
          <h4>Componentes del combo</h4>
          {itemDrafts.map((item) => {
            const resolvedDeviceOptions = deviceOptions.some(
              (option) => option.value === item.deviceId,
            )
              ? deviceOptions
              : item.deviceId
              ? [
                  {
                    value: item.deviceId,
                    label: item.deviceLabel ?? `Dispositivo #${item.deviceId}`,
                  },
                  ...deviceOptions,
                ]
              : deviceOptions;

            const variantOptions = (() => {
              if (!enableVariants || !item.deviceId) {
                return [] as Array<{ value: string; label: string }>;
              }
              const numericDeviceId = Number.parseInt(item.deviceId, 10);
              const availableVariants = variants.items.filter(
                (variant) => variant.device_id === numericDeviceId,
              );
              const mapped = availableVariants.map((variant) => ({
                value: String(variant.id),
                label: variant.name,
              }));
              if (
                item.variantId &&
                !mapped.some((option) => option.value === item.variantId) &&
                item.variantLabel
              ) {
                return [{ value: item.variantId, label: item.variantLabel }, ...mapped];
              }
              return mapped;
            })();

            return (
              <div key={item.key}>
                <div className="form-row">
                  <label htmlFor={`device-${item.key}`}>Dispositivo</label>
                  <select
                    id={`device-${item.key}`}
                    value={item.deviceId}
                    onChange={(event) => handleItemDeviceChange(item.key, event.target.value)}
                    required
                  >
                    <option value="">Selecciona un dispositivo</option>
                    {resolvedDeviceOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                {enableVariants ? (
                  <div className="form-row">
                    <label htmlFor={`variant-${item.key}`}>Variante (opcional)</label>
                    <select
                      id={`variant-${item.key}`}
                      value={item.variantId}
                      onChange={(event) => handleItemVariantChange(item.key, event.target.value)}
                    >
                      <option value="">Usar configuración base</option>
                      {variantOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : null}
                <div className="form-row">
                  <label htmlFor={`quantity-${item.key}`}>Cantidad</label>
                  <input
                    id={`quantity-${item.key}`}
                    type="number"
                    min="1"
                    value={item.quantity}
                    onChange={(event) => handleItemQuantityChange(item.key, event.target.value)}
                  />
                </div>
                <div className="form-row">
                  <button
                    type="button"
                    className="danger"
                    onClick={() => handleRemoveItem(item.key)}
                  >
                    Quitar
                  </button>
                </div>
              </div>
            );
          })}
          <button type="button" className="secondary" onClick={handleAddItem}>
            Agregar componente
          </button>
        </div>

        <div className="form-actions">
          <button type="submit" className="primary">
            {formState.editingId ? "Actualizar combo" : "Crear combo"}
          </button>
          {formState.editingId ? (
            <button type="button" className="secondary" onClick={resetForm}>
              Cancelar
            </button>
          ) : null}
        </div>
      </form>
    </section>
  );
}

export default InventoryBundlesSection;
