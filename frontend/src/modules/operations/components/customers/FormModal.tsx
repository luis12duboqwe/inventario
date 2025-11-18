import type { FormEvent } from "react";
import type { CustomerFormState } from "../../../../types/customers";

type Option = { value: string; label: string };

type CustomersFormModalProps = {
  formState: CustomerFormState;
  customerTypes: Option[];
  customerStatuses: Option[];
  savingCustomer: boolean;
  editingId: number | null;
  loadingCustomers: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onFormChange: <Field extends keyof CustomerFormState>(
    field: Field,
    value: CustomerFormState[Field],
  ) => void;
  onCancelEdit: () => void;
  onExportCsv: () => void;
};

const CustomersFormModal = ({
  formState,
  customerTypes,
  customerStatuses,
  savingCustomer,
  editingId,
  loadingCustomers,
  onSubmit,
  onFormChange,
  onCancelEdit,
  onExportCsv,
}: CustomersFormModalProps) => {
  return (
    <div className="panel">
      <div className="panel__header">
        <h2>Registro y actualización de clientes</h2>
        <p className="panel__subtitle">
          Mantén al día la información corporativa, el saldo pendiente y las notas de seguimiento de tus clientes.
        </p>
      </div>
      <form className="form-grid" onSubmit={onSubmit}>
        <label>
          Nombre del cliente
          <input
            value={formState.name}
            onChange={(event) => onFormChange("name", event.target.value)}
            placeholder="Ej. SuperCell Distribuciones"
            required
          />
        </label>
        <label>
          Contacto principal
          <input
            value={formState.contactName}
            onChange={(event) => onFormChange("contactName", event.target.value)}
            placeholder="Nombre del contacto"
          />
        </label>
        <label>
          Teléfono
          <input
            value={formState.phone}
            onChange={(event) => onFormChange("phone", event.target.value)}
            placeholder="10 dígitos"
            required
          />
        </label>
        <label>
          Correo electrónico
          <input
            type="email"
            value={formState.email}
            onChange={(event) => onFormChange("email", event.target.value)}
            placeholder="contacto@empresa.com"
          />
        </label>
        <label>
          Dirección
          <input
            value={formState.address}
            onChange={(event) => onFormChange("address", event.target.value)}
            placeholder="Calle, número y ciudad"
          />
        </label>
        <label>
          RTN para facturación
          <input
            value={formState.taxId}
            onChange={(event) => onFormChange("taxId", event.target.value)}
            placeholder="RTN corporativo"
            required
          />
          <span className="muted-text">Se usa en facturación y recibos. Debe tener al menos 5 caracteres.</span>
        </label>
        <label>
          Tipo de cliente
          <select
            value={formState.customerType}
            onChange={(event) => onFormChange("customerType", event.target.value)}
          >
            {customerTypes.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Estado
          <select
            value={formState.status}
            onChange={(event) => onFormChange("status", event.target.value)}
          >
            {customerStatuses.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Categoría de segmentación
          <input
            value={formState.segmentCategory}
            onChange={(event) => onFormChange("segmentCategory", event.target.value)}
            placeholder="Ej. alto_valor, frecuente"
          />
        </label>
        <label>
          Etiquetas
          <input
            value={formState.tags}
            onChange={(event) => onFormChange("tags", event.target.value)}
            placeholder="Separadas por coma: vip,fintech,lealtad"
          />
          <span className="muted-text">Se aplican como filtros combinados y se sincronizan entre sucursales.</span>
        </label>
        <label>
          Límite de crédito MXN
          <input
            type="number"
            min={0}
            value={formState.creditLimit}
            onChange={(event) => onFormChange("creditLimit", Number(event.target.value))}
          />
        </label>
        <label>
          Saldo pendiente MXN
          <input
            type="number"
            min={0}
            value={formState.outstandingDebt}
            onChange={(event) => onFormChange("outstandingDebt", Number(event.target.value))}
          />
        </label>
        <label className="span-2">
          Notas internas
          <textarea
            rows={2}
            value={formState.notes}
            onChange={(event) => onFormChange("notes", event.target.value)}
            placeholder="Instrucciones especiales, condiciones de crédito o preferencias"
          />
        </label>
        <label className="span-2">
          Nota para historial
          <textarea
            rows={2}
            value={formState.historyNote}
            onChange={(event) => onFormChange("historyNote", event.target.value)}
            placeholder="Se agregará al historial de contacto al guardar"
          />
        </label>
        <div className="actions-row">
          <button type="submit" className="btn btn--primary" disabled={savingCustomer}>
            {savingCustomer
              ? "Guardando..."
              : editingId
              ? "Actualizar cliente"
              : "Registrar cliente"}
          </button>
          {editingId ? (
            <button
              type="button"
              className="btn btn--ghost"
              onClick={onCancelEdit}
              disabled={savingCustomer}
            >
              Cancelar edición
            </button>
          ) : null}
          <button
            type="button"
            className="btn btn--secondary"
            onClick={onExportCsv}
            disabled={loadingCustomers}
          >
            Exportar CSV
          </button>
        </div>
      </form>
    </div>
  );
};

export default CustomersFormModal;
