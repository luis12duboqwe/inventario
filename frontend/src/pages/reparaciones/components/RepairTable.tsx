import type { ReactNode } from "react";

import type { RepairOrder } from "../../../api";
import LoadingOverlay from "../../../shared/components/LoadingOverlay";
import ScrollableTable from "../../../shared/components/ScrollableTable";

type RepairTableProps = {
  loading: boolean;
  orders: RepairOrder[];
  renderHead: () => ReactNode;
  renderRow: (order: RepairOrder) => ReactNode;
  emptyMessage?: string;
};

function RepairTable({
  loading,
  orders,
  renderHead,
  renderRow,
  emptyMessage = "No hay órdenes con los filtros actuales.",
}: RepairTableProps) {
  return (
    <div className="repair-orders-table">
      <LoadingOverlay visible={loading} label="Cargando órdenes de reparación..." />
      {orders.length === 0 ? (
        !loading ? <p className="muted-text">{emptyMessage}</p> : null
      ) : (
        <ScrollableTable
          items={orders}
          itemKey={(order) => order.id}
          title="Órdenes de reparación"
          ariaLabel="Tabla de órdenes de reparación"
          renderHead={renderHead}
          renderRow={renderRow}
        />
      )}
    </div>
  );
}

export type { RepairTableProps };
export default RepairTable;
