import { useState } from "react";
import Modal from "@components/ui/Modal";

export type PrintOptions = {
  includePrice: boolean;
  includeLogo: boolean;
  labelSize: "small" | "medium" | "large";
  template: "standard" | "price_tag" | "inventory_tag";
};

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (options: PrintOptions) => void;
  deviceCount: number;
};

export default function PrintLabelDialog({ isOpen, onClose, onConfirm, deviceCount }: Props) {
  const [options, setOptions] = useState<PrintOptions>({
    includePrice: true,
    includeLogo: true,
    labelSize: "medium",
    template: "standard",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConfirm(options);
  };

  return (
    <Modal open={isOpen} onClose={onClose} title={`Imprimir etiquetas (${deviceCount})`} size="sm">
      <form onSubmit={handleSubmit} className="print-options-form flex flex-col gap-6">
        <div className="form-group flex flex-col gap-2">
          <label htmlFor="template-select" className="text-muted-foreground text-sm font-medium">
            Plantilla de diseño
          </label>
          <select
            id="template-select"
            value={options.template}
            onChange={(e) =>
              setOptions({ ...options, template: e.target.value as PrintOptions["template"] })
            }
            className="ui-field w-full p-3 rounded-md border border-border-subtle bg-surface text-text-primary"
          >
            <option value="standard">Estándar (Info + QR)</option>
            <option value="price_tag">Etiqueta de Precio (Precio grande)</option>
            <option value="inventory_tag">Control de Inventario (SKU/IMEI grande)</option>
          </select>
        </div>

        <div className="form-group flex flex-col gap-2">
          <label className="checkbox-label flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={options.includePrice}
              onChange={(e) => setOptions({ ...options, includePrice: e.target.checked })}
              className="w-5 h-5 accent-accent"
            />
            <span className="text-text-primary">Incluir precio de venta</span>
          </label>
        </div>
        <div className="form-group flex flex-col gap-2">
          <label className="checkbox-label flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={options.includeLogo}
              onChange={(e) => setOptions({ ...options, includeLogo: e.target.checked })}
              className="w-5 h-5 accent-accent"
            />
            <span className="text-text-primary">Incluir logotipo corporativo</span>
          </label>
        </div>
        <div className="form-group flex flex-col gap-2">
          <label htmlFor="label-size-select" className="text-muted-foreground text-sm font-medium">
            Tamaño de etiqueta
          </label>
          <select
            id="label-size-select"
            value={options.labelSize}
            onChange={(e) =>
              setOptions({ ...options, labelSize: e.target.value as PrintOptions["labelSize"] })
            }
            className="ui-field w-full p-3 rounded-md border border-border-subtle bg-surface text-text-primary"
          >
            <option value="small">Pequeña (50x25mm)</option>
            <option value="medium">Mediana (70x35mm)</option>
            <option value="large">Grande (100x50mm)</option>
          </select>
        </div>
        <div className="modal-actions flex justify-end gap-4 mt-4">
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Cancelar
          </button>
          <button type="submit" className="btn btn--primary">
            Imprimir
          </button>
        </div>
      </form>
    </Modal>
  );
}
