import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import {
  TransfersFiltersBar,
  TransfersSummaryCards,
  TransfersTable,
  TransfersSidePanel,
} from "../components/transfers/list";
import type { TransferFilters, TransferRow } from "../components/transfers/list";
import { listTransfers, type TransferOrder } from "@api/transfers";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { FILTER_ALL_VALUE } from "@/config/constants";

function TransfersListPage() {
  const navigate = useNavigate();
  const { token, stores, selectedStoreId, pushToast } = useDashboard();
  const [filters, setFilters] = useState<TransferFilters>({});
  const [transfers, setTransfers] = useState<TransferOrder[]>([]);
  const [loading, setLoading] = useState(false);

  type EnrichedRow = TransferRow & {
    rawStatus: TransferOrder["status"];
    createdAt: string;
    updatedAt: string;
    reason?: string;
    createdBy?: string;
  };

  const [selected, setSelected] = useState<EnrichedRow | null>(null);

  const loadTransfers = useCallback(async () => {
    if (!token) {
      return;
    }
    setLoading(true);
    try {
      const data = await listTransfers(token, selectedStoreId ?? undefined);
      setTransfers(data);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No fue posible cargar las transferencias";
      pushToast({ message, variant: "error" });
    } finally {
      setLoading(false);
    }
  }, [pushToast, selectedStoreId, token]);

  useEffect(() => {
    void loadTransfers();
  }, [loadTransfers]);

  const storeMap = useMemo(() => {
    const entries = stores.map((store) => [store.id, store.name] as const);
    return new Map(entries);
  }, [stores]);

  const statusLabels: Record<string, string> = useMemo(
    () => ({
      SOLICITADA: "Solicitada",
      EN_TRANSITO: "En tránsito",
      RECIBIDA: "Recibida",
      CANCELADA: "Cancelada",
    }),
    [],
  );

  const normalizedRows = useMemo<EnrichedRow[]>(() => {
    return transfers
      .map((transfer) => {
        const origin = storeMap.get(transfer.origin_store_id) ?? `#${transfer.origin_store_id}`;
        const destination =
          storeMap.get(transfer.destination_store_id) ?? `#${transfer.destination_store_id}`;
        const quantity = transfer.items.reduce((sum, item) => sum + (item.quantity ?? 0), 0);
        const formattedNumber = `TRF-${String(transfer.id).padStart(6, "0")}`;
        const rawStatus = transfer.status;
        const row: EnrichedRow = {
          id: String(transfer.id),
          date: transfer.created_at,
          number: formattedNumber,
          from: origin,
          to: destination,
          items: quantity,
          status: statusLabels[rawStatus] ?? rawStatus,
          rawStatus,
          createdAt: transfer.created_at,
          updatedAt: transfer.updated_at,
        };
        if (transfer.reason) {
          row.reason = transfer.reason;
        }
        if (transfer.ultima_accion?.usuario) {
          row.createdBy = transfer.ultima_accion.usuario;
        }
        return row;
      })
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  }, [statusLabels, storeMap, transfers]);

  const filteredRows = useMemo<EnrichedRow[]>(() => {
    return normalizedRows.filter((row) => {
      const queryMatch = filters.query
        ? [row.number, row.from, row.to, row.reason]
            .filter(Boolean)
            .some((value) => value?.toLowerCase().includes(filters.query!.toLowerCase()))
        : true;
      if (!queryMatch) {
        return false;
      }
      const rowStatus = row.rawStatus ?? row.status;
      if (filters.status && filters.status !== FILTER_ALL_VALUE && rowStatus !== filters.status) {
        return false;
      }
      if (filters.from && !row.from?.toLowerCase().includes(filters.from.toLowerCase())) {
        return false;
      }
      if (filters.to && !row.to?.toLowerCase().includes(filters.to.toLowerCase())) {
        return false;
      }
      if (filters.dateFrom) {
        const fromDate = new Date(filters.dateFrom);
        if (new Date(row.date) < fromDate) {
          return false;
        }
      }
      if (filters.dateTo) {
        const toDate = new Date(filters.dateTo);
        const rowDate = new Date(row.date);
        if (rowDate > new Date(toDate.getTime() + 24 * 60 * 60 * 1000)) {
          return false;
        }
      }
      return true;
    });
  }, [
    filters.dateFrom,
    filters.dateTo,
    filters.from,
    filters.query,
    filters.status,
    filters.to,
    normalizedRows,
  ]);

  useEffect(() => {
    if (!selected) {
      return;
    }
    const match = filteredRows.find((row) => row.id === selected.id);
    if (!match) {
      setSelected(null);
    } else if (match !== selected) {
      setSelected(match);
    }
  }, [filteredRows, selected]);

  const summaryItems = useMemo(() => {
    const totals = filteredRows.reduce((acc, row) => {
      const statusKey = row.rawStatus ?? row.status;
      acc[statusKey] = (acc[statusKey] ?? 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    return [
      { label: "Solicitadas", value: totals.SOLICITADA ?? 0 },
      { label: "En tránsito", value: totals.EN_TRANSITO ?? 0, status: "in-progress" as const },
      { label: "Recibidas", value: totals.RECIBIDA ?? 0, status: "success" as const },
      { label: "Canceladas", value: totals.CANCELADA ?? 0, status: "danger" as const },
    ];
  }, [filteredRows]);

  const handleRowClick = useCallback(
    (row: TransferRow) => {
      const enriched = filteredRows.find((item) => item.id === row.id);
      if (enriched) {
        setSelected(enriched);
      } else {
        setSelected({
          ...row,
          rawStatus: row.status as TransferOrder["status"],
          createdAt: row.date,
          updatedAt: row.date,
        });
      }
    },
    [filteredRows, setSelected],
  );

  const handleNavigateToTransfers = () => {
    navigate("/dashboard/operations/transferencias");
  };

  return (
    <div className="inventory-page">
      <PageHeader
        title="Transferencias"
        subtitle="Gestión de envíos entre sucursales y almacenes."
        actions={[
          {
            label: "Nueva transferencia",
            onClick: handleNavigateToTransfers,
            variant: "primary",
          },
        ]}
      />

      <TransfersSummaryCards items={summaryItems} loading={loading && filteredRows.length === 0} />

      <PageToolbar>
        <TransfersFiltersBar
          value={filters}
          onChange={setFilters}
          onNew={handleNavigateToTransfers}
        />
      </PageToolbar>

      <TransfersTable rows={filteredRows} loading={loading} onRowClick={handleRowClick} />

      <TransfersSidePanel
        row={
          selected
            ? {
                ...selected,
                ...(selected.reason ? { notes: selected.reason } : {}),
              }
            : null
        }
        onClose={() => setSelected(null)}
      />
    </div>
  );
}

export default TransfersListPage;
