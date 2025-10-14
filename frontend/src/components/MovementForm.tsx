import { FormEvent, useEffect, useState } from "react";
import { Device, MovementInput } from "../api";

type Props = {
  devices: Device[];
  onSubmit: (payload: MovementInput) => Promise<void> | void;
};

function MovementForm({ devices, onSubmit }: Props) {
  const [deviceId, setDeviceId] = useState<number | "">(devices[0]?.id ?? "");
  const [movementType, setMovementType] = useState<MovementInput["movement_type"]>("entrada");
  const [quantity, setQuantity] = useState(1);
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (devices.length > 0) {
      setDeviceId(devices[0].id);
    }
  }, [devices]);

  if (devices.length === 0) {
    return <p>Registra al menos un dispositivo para habilitar los movimientos.</p>;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!deviceId) {
      return;
    }
    await onSubmit({
      device_id: Number(deviceId),
      movement_type: movementType,
      quantity,
      reason: reason.trim() || undefined,
    });
    setQuantity(1);
    setReason("");
  };

  return (
    <form onSubmit={handleSubmit} className="movement-form">
      <label htmlFor="deviceId">Dispositivo</label>
      <select
        id="deviceId"
        value={deviceId ?? ""}
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
      <select id="movementType" value={movementType} onChange={(event) => setMovementType(event.target.value as MovementInput["movement_type"])}>
        <option value="entrada">Entrada</option>
        <option value="salida">Salida</option>
        <option value="ajuste">Ajuste</option>
      </select>

      <label htmlFor="quantity">Cantidad</label>
      <input
        id="quantity"
        type="number"
        min={movementType === "ajuste" ? 0 : 1}
        value={quantity}
        onChange={(event) => setQuantity(Number(event.target.value))}
        required
      />

      <label htmlFor="reason">Motivo corporativo</label>
      <textarea
        id="reason"
        rows={2}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        placeholder="Describe el motivo (mínimo 5 caracteres)"
        minLength={5}
        required
      />

      <button type="submit">Registrar movimiento</button>
    </form>
  );
}

export default MovementForm;
