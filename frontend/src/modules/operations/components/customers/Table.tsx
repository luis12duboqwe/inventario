import type { Customer } from "@api/customers";

type CustomersTableProps = {
  customers: Customer[];
  loading: boolean;
  selectedCustomerId: number | null;
  formatCurrency: (value: number) => string;
  onSelect: (customer: Customer) => void;
  onEdit: (customer: Customer) => void;
  onAddNote: (customer: Customer) => void;
  onRegisterPayment: (customer: Customer) => void;
  onAdjustDebt: (customer: Customer) => void;
  onDelete: (customer: Customer) => void;
};

const CustomersTable = ({
  customers,
  loading,
  selectedCustomerId,
  formatCurrency,
  onSelect,
  onEdit,
  onAddNote,
  onRegisterPayment,
  onAdjustDebt,
  onDelete,
}: CustomersTableProps) => {
  if (loading) {
    return <p className="muted-text">Cargando clientes...</p>;
  }

  if (customers.length === 0) {
    return (
      <p className="muted-text">No hay clientes que coincidan con los filtros seleccionados.</p>
    );
  }

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Tipo</th>
            <th>Categoría</th>
            <th>Etiquetas</th>
            <th>Estado</th>
            <th>Contacto</th>
            <th>Correo</th>
            <th>Teléfono</th>
            <th>RTN</th>
            <th>Límite crédito</th>
            <th>Saldo</th>
            <th>Última interacción</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {customers.map((customer) => {
            const lastInteraction = customer.last_interaction_at
              ? new Date(customer.last_interaction_at).toLocaleString("es-HN")
              : "—";
            const creditLimit = Number(customer.credit_limit ?? 0);
            const debt = Number(customer.outstanding_debt ?? 0);
            const category = customer.segment_category ?? "—";
            const tags = Array.isArray(customer.tags) ? customer.tags.join(", ") : "";
            const statusClass =
              customer.status === "moroso"
                ? "badge warning"
                : customer.status === "activo"
                ? "badge success"
                : "badge neutral";
            return (
              <tr
                key={customer.id}
                className={selectedCustomerId === customer.id ? "is-selected" : undefined}
              >
                <td>#{customer.id}</td>
                <td>
                  <strong>{customer.name}</strong>
                  <div className="muted-text small">
                    Registrado el {new Date(customer.created_at).toLocaleDateString("es-HN")}
                  </div>
                </td>
                <td>{customer.customer_type ?? "—"}</td>
                <td>{category}</td>
                <td>{tags || "—"}</td>
                <td>
                  <span className={statusClass}>{customer.status ?? "—"}</span>
                </td>
                <td>{customer.contact_name ?? "—"}</td>
                <td>{customer.email ?? "—"}</td>
                <td>{customer.phone}</td>
                <td>{customer.tax_id}</td>
                <td>${formatCurrency(creditLimit)}</td>
                <td>${formatCurrency(debt)}</td>
                <td>{lastInteraction}</td>
                <td>
                  <div className="customer-actions">
                    <button
                      type="button"
                      className="btn btn--link"
                      onClick={() => onSelect(customer)}
                    >
                      Perfil
                    </button>
                    <button
                      type="button"
                      className="btn btn--link"
                      onClick={() => onEdit(customer)}
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      className="btn btn--link"
                      onClick={() => onAddNote(customer)}
                    >
                      Nota
                    </button>
                    <button
                      type="button"
                      className="btn btn--link"
                      onClick={() => onRegisterPayment(customer)}
                    >
                      Pago
                    </button>
                    <button
                      type="button"
                      className="btn btn--link"
                      onClick={() => onAdjustDebt(customer)}
                    >
                      Ajustar saldo
                    </button>
                    <button
                      type="button"
                      className="btn btn--link"
                      onClick={() => onDelete(customer)}
                    >
                      Eliminar
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default CustomersTable;
