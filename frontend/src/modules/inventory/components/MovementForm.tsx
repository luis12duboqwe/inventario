import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { Device, MovementInput } from "@api/inventory";
import Button from "@components/ui/Button";
import "./MovementForm.css";

type Props = {
  devices: Device[];
  onSubmit: (payload: MovementInput) => Promise<void> | void;
};

type FormValues = {
  deviceId: string;
  movementType: MovementInput["tipo_movimiento"];
  quantity: number;
  unitCost: string;
  comment: string;
};

function MovementForm({ devices, onSubmit }: Props) {
  const {
    register,
    handleSubmit,
    control,
    reset,
    setValue,
    formState: { isSubmitting, errors },
  } = useForm<FormValues>({
    defaultValues: {
      deviceId: "",
      movementType: "entrada",
      quantity: 1,
      unitCost: "",
      comment: "",
    },
  });

  // Set default device when devices list loads
  useEffect(() => {
    if (devices.length > 0) {
      setValue("deviceId", String(devices[0].id));
    }
  }, [devices, setValue]);

  const movementType = useWatch({ control, name: "movementType" });

  const onSubmitForm = async (data: FormValues) => {
    if (!data.deviceId) return;

    const normalizedComment = data.comment.trim();
    const rawUnitCost = data.unitCost.trim();
    const shouldSendUnitCost = data.movementType === "entrada" && rawUnitCost.length > 0;
    const parsedUnitCost = shouldSendUnitCost ? Number(rawUnitCost) : undefined;

    const payload: MovementInput = {
      producto_id: Number(data.deviceId),
      tipo_movimiento: data.movementType,
      cantidad: data.quantity,
      comentario: normalizedComment,
    };

    if (
      typeof parsedUnitCost === "number" &&
      Number.isFinite(parsedUnitCost) &&
      parsedUnitCost >= 0
    ) {
      payload.unit_cost = parsedUnitCost;
    }

    await onSubmit(payload);

    reset({
      deviceId: data.deviceId,
      movementType: data.movementType,
      quantity: 1,
      unitCost: "",
      comment: "",
    });
  };

  if (devices.length === 0) {
    return <p>Registra al menos un dispositivo para habilitar los movimientos.</p>;
  }

  return (
    <form onSubmit={handleSubmit(onSubmitForm)} className="movement-form">
      <label>
        <span>Dispositivo</span>
        <select {...register("deviceId", { required: "Selecciona un dispositivo" })}>
          <option value="" disabled>
            Selecciona un equipo
          </option>
          {devices.map((device) => (
            <option key={device.id} value={device.id}>
              {device.sku} · {device.name}
            </option>
          ))}
        </select>
        {errors.deviceId && (
          <span className="error-text text-danger text-sm">{errors.deviceId.message}</span>
        )}
      </label>

      <label>
        <span>Tipo de movimiento</span>
        <select {...register("movementType")}>
          <option value="entrada">Entrada</option>
          <option value="salida">Salida</option>
          <option value="ajuste">Ajuste</option>
        </select>
      </label>

      <label>
        <span>Cantidad</span>
        <input
          type="number"
          min={1}
          step={1}
          {...register("quantity", {
            required: true,
            min: 1,
            valueAsNumber: true,
          })}
        />
      </label>

      {movementType === "entrada" && (
        <label>
          <span>Costo unitario (MXN)</span>
          <input
            type="number"
            min={0}
            step={0.01}
            placeholder="Ej. 8,599.99"
            {...register("unitCost")}
          />
        </label>
      )}

      <label>
        <span>Motivo corporativo</span>
        <textarea
          rows={2}
          placeholder="Describe el motivo (mínimo 5 caracteres)"
          {...register("comment", {
            required: "El motivo es obligatorio",
            minLength: { value: 5, message: "Mínimo 5 caracteres" },
          })}
        />
        {errors.comment && (
          <span className="error-text text-danger text-sm">{errors.comment.message}</span>
        )}
      </label>

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Registrando..." : "Registrar movimiento"}
      </Button>
    </form>
  );
}

export default MovementForm;
