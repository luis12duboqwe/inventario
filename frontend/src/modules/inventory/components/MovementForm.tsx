import { FormEvent, useMemo, useState } from "react";
import { Device, MovementInput } from "../../../api";

type Props = {
  devices: Device[];
  onSubmit: (payload: MovementInput) => Promise<void> | void;
};

function MovementForm({ devices, onSubmit }: Props) {
  const [deviceId, setDeviceId] = useState<number | "">(devices[0]?.id ?? "");
  const [movementType, setMovementType] = useState<MovementInput["tipo_movimiento"]>("entrada");
  const [quantity, setQuantity] = useState(1);
  const [comment, setComment] = useState("");
  const [unitCost, setUnitCost] = useState("");

  // Derivar el dispositivo efectivo sin setState en efectos: si no hay selección explicita, usar el primero.
  const effectiveDeviceId = useMemo<number | "">(
    () => (deviceId === "" ? (devices[0]?.id ?? "") : deviceId),
    [deviceId, devices],
  );

  if (devices.length === 0) {
    return <p>Registra al menos un dispositivo para habilitar los movimientos.</p>;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!deviceId) {
      return;
    }
    const normalizedComment = comment.trim();
    const rawUnitCost = unitCost.trim();
    const shouldSendUnitCost = movementType === "entrada" && rawUnitCost.length > 0;
    const parsedUnitCost = shouldSendUnitCost ? Number(rawUnitCost) : undefined;

    const payload: MovementInput = {
      producto_id: Number(deviceId),
      tipo_movimiento: movementType,
      cantidad: quantity,
      comentario: normalizedComment,
    };

    if (typeof parsedUnitCost === "number" && Number.isFinite(parsedUnitCost) && parsedUnitCost >= 0) {
      payload.unit_cost = parsedUnitCost;
    }

    await onSubmit(payload);
    setQuantity(1);
    setComment("");
    setUnitCost("");
  };

  return (
    <form onSubmit={handleSubmit} className="movement-form">
      <label htmlFor="deviceId">Dispositivo</label>
      <select
        id="deviceId"
        value={effectiveDeviceId ?? ""}
        onChange={(event) => setDeviceId(event.target.value ? Number(event.target.value) : "")}
        required
      >
        <option value="" disabled>
          Selecciona un equipo
        </option>
        {devices.map((device) => (
          <option key={device.id} value={device.id}>
            {device.sku} · {device.name}
          </option>
        ))}
      </select>

      <label htmlFor="movementType">Tipo de movimiento</label>
      <select
        id="movementType"
        value={movementType}
        onChange={(event) => setMovementType(event.target.value as MovementInput["tipo_movimiento"])}
      >
        <option value="entrada">Entrada</option>
        <option value="salida">Salida</option>
        <option value="ajuste">Ajuste</option>
      </select>

      <label htmlFor="quantity">Cantidad</label>
      <input
        id="quantity"
        type="number"
        min={1}
        step={1}
        value={quantity}
        onChange={(event) => {
          const nextValue = Number(event.target.value);
          if (!Number.isFinite(nextValue)) {
            setQuantity(1);
            return;
          }
          setQuantity(Math.max(1, Math.floor(nextValue)));
        }}
        required
      />

      {movementType === "entrada" ? (
        <>
          <label htmlFor="unitCost">Costo unitario (MXN)</label>
          <input
            id="unitCost"
            type="number"
            min={0}
            step={0.01}
            value={unitCost}
            onChange={(event) => setUnitCost(event.target.value)}
            placeholder="Ej. 8,599.99"
          />
        </>
      ) : null}

      <label htmlFor="comment">Motivo corporativo</label>
      <textarea
        id="comment"
        rows={2}
        value={comment}
        onChange={(event) => setComment(event.target.value)}
        placeholder="Describe el motivo (mínimo 5 caracteres)"
        minLength={5}
        required
      />

      <button type="submit">Registrar movimiento</button>
    </form>
  );
}

export default MovementForm;
