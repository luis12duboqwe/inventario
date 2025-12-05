import React from "react";
import { Modal } from "../../../../../components/ui/Modal";
import { Button } from "../../../../../components/ui/Button";
import { TextField } from "../../../../../components/ui/TextField";

export type MovementCreatePayload = {
  type: "IN" | "OUT" | "TRANSFER";
  productId: string;
  qty: number;
  fromStoreId?: string;
  toStoreId?: string;
  reference?: string;
  note?: string;
};

type Props = {
  open?: boolean;
  onClose?: () => void;
  onCreate?: (payload: MovementCreatePayload) => void;
};

export default function CreateModal({ open, onClose, onCreate }: Props) {
  const [type, setType] = React.useState<"IN" | "OUT" | "TRANSFER">("IN");
  const [productId, setProductId] = React.useState("");
  const [qty, setQty] = React.useState<string>("");
  const [fromStoreId, setFromStoreId] = React.useState("");
  const [toStoreId, setToStoreId] = React.useState("");
  const [reference, setReference] = React.useState("");
  const [note, setNote] = React.useState("");

  React.useEffect(() => {
    if (!open) {
      setType("IN");
      setProductId("");
      setQty("");
      setFromStoreId("");
      setToStoreId("");
      setReference("");
      setNote("");
    }
  }, [open]);

  if (!open) return null;
  const validQty = qty ? Number(qty) : NaN;

  return (
    <Modal
      isOpen={open}
      onClose={onClose}
      title="Nuevo movimiento"
      footer={
        <div className="flex gap-2 justify-end">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              if (!productId || Number.isNaN(validQty) || validQty === 0) return;
              const payload: MovementCreatePayload = {
                type,
                productId,
                qty: Number(validQty),
                reference,
                note,
              };
              if (type === "TRANSFER") {
                payload.fromStoreId = fromStoreId;
                payload.toStoreId = toStoreId;
              } else {
                payload.toStoreId = toStoreId;
              }
              onCreate?.(payload);
            }}
          >
            Crear
          </Button>
        </div>
      }
    >
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-muted-foreground">Tipo</label>
          <select
            value={type}
            onChange={(e) => setType(e.target.value as "IN" | "OUT" | "TRANSFER")}
            className="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="IN">Entrada</option>
            <option value="OUT">Salida</option>
            <option value="TRANSFER">Transferencia</option>
          </select>
        </div>
        <TextField
          label="Product ID"
          value={productId}
          onChange={(e) => setProductId(e.target.value)}
        />
        <TextField
          label="Cantidad"
          type="number"
          value={qty}
          onChange={(e) => setQty(e.target.value)}
        />
        {type === "TRANSFER" ? (
          <>
            <TextField
              label="De (fromStoreId)"
              value={fromStoreId}
              onChange={(e) => setFromStoreId(e.target.value)}
            />
            <TextField
              label="A (toStoreId)"
              value={toStoreId}
              onChange={(e) => setToStoreId(e.target.value)}
            />
          </>
        ) : (
          <>
            <TextField
              label="Sucursal (storeId)"
              value={toStoreId}
              onChange={(e) => setToStoreId(e.target.value)}
            />
            <div />
          </>
        )}
        <TextField
          label="Referencia (opcional)"
          value={reference}
          onChange={(e) => setReference(e.target.value)}
        />
        <TextField label="Nota (opcional)" value={note} onChange={(e) => setNote(e.target.value)} />
      </div>
    </Modal>
  );
}
