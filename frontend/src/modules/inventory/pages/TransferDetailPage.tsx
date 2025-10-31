import { useMemo, useState } from "react";
import PageHeader from "../../../components/layout/PageHeader";
import {
  TransferHeader,
  TransferItemsTable,
  TransferTimeline,
  TransferActionsBar,
  PickModal,
  PackModal,
  ShipModal,
  ReceiveModal,
} from "../components/transfers/detail";
import type {
  PickLine,
  ReceiveLine,
  TimelineStep,
  TransferItemLine,
} from "../components/transfers/detail";

function TransferDetailPage() {
  const transfer = useMemo<{
    number?: string;
    status?: string;
    from?: string;
    to?: string;
    items?: TransferItemLine[];
    steps?: TimelineStep[];
  }>(() => ({
    // TODO(wire): cargar transferencia seleccionada
    items: [],
    steps: [],
  }), []);

  const [pickOpen, setPickOpen] = useState(false);
  const [packOpen, setPackOpen] = useState(false);
  const [shipOpen, setShipOpen] = useState(false);
  const [receiveOpen, setReceiveOpen] = useState(false);

  const pickLines = useMemo<PickLine[]>(() => {
    if (!Array.isArray(transfer.items)) {
      return [];
    }
    return transfer.items.map((item) => ({
      id: item.id,
      name: item.name,
      qty: item.qty,
      picked: item.picked,
    }));
  }, [transfer.items]);

  const receiveLines = useMemo<ReceiveLine[]>(() => {
    if (!Array.isArray(transfer.items)) {
      return [];
    }
    return transfer.items.map((item) => ({
      id: item.id,
      name: item.name,
      qty: item.qty,
      shipped: item.shipped,
      allowSerial: Boolean(item.imeis && item.imeis.length > 0),
    }));
  }, [transfer.items]);

  return (
    <div className="inventory-page">
      <PageHeader title="Detalle de transferencia" subtitle="Seguimiento y acciones operativas." />

      <TransferHeader
        number={transfer.number}
        status={transfer.status}
        from={transfer.from}
        to={transfer.to}
        onPick={() => setPickOpen(true)}
        onPack={() => setPackOpen(true)}
        onShip={() => setShipOpen(true)}
        onReceive={() => setReceiveOpen(true)}
        onCancel={() => {
          // TODO(wire): cancelar transferencia
        }}
      />

      <TransferTimeline steps={transfer.steps} />

      <TransferItemsTable items={transfer.items} />

      <TransferActionsBar
        onPick={() => setPickOpen(true)}
        onPack={() => setPackOpen(true)}
        onShip={() => setShipOpen(true)}
        onReceive={() => setReceiveOpen(true)}
        onPrint={() => {
          // TODO(wire): imprimir nota
        }}
      />

      <PickModal
        open={pickOpen}
        lines={pickLines}
        onClose={() => setPickOpen(false)}
        onSubmit={(payload) => {
          void payload;
          // TODO(wire): confirmar picking
          setPickOpen(false);
        }}
      />

      <PackModal
        open={packOpen}
        onClose={() => setPackOpen(false)}
        onSubmit={(payload) => {
          void payload;
          // TODO(wire): confirmar empaquetado
          setPackOpen(false);
        }}
      />

      <ShipModal
        open={shipOpen}
        onClose={() => setShipOpen(false)}
        onSubmit={(payload) => {
          void payload;
          // TODO(wire): confirmar envío
          setShipOpen(false);
        }}
      />

      <ReceiveModal
        open={receiveOpen}
        lines={receiveLines}
        onClose={() => setReceiveOpen(false)}
        onSubmit={(payload) => {
          void payload;
          // TODO(wire): confirmar recepción
          setReceiveOpen(false);
        }}
      />
    </div>
  );
}

export default TransferDetailPage;
