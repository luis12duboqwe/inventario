import { Skeleton } from "@/ui/Skeleton"; // [PACK36-pos]
import { safeArray } from "@/utils/safeValues"; // [PACK36-pos]
import Button from "../../../../shared/components/ui/Button";
import Modal from "../../../../shared/components/ui/Modal";
import CartPanel from "../../../../pages/pos/components/CartPanel";
import PaymentModal from "../../../../pages/pos/components/PaymentModal";
import ProductGrid from "../../../../pages/pos/components/ProductGrid";
import QuickSaleForm from "../../../../pages/pos/components/QuickSaleForm";
import ReceiptPreview from "../../../../pages/pos/components/ReceiptPreview";
import Toolbar from "../../../../pages/pos/components/Toolbar";
import CashRegisterModule from "../../cash/CashRegister";
import POSSettings from "./POSSettings";
import {
  usePosDashboardController,
  type UsePosDashboardControllerParams,
} from "./usePosDashboardController";

type Props = UsePosDashboardControllerParams;

function POSDashboard(props: Props) {
  const {
    alerts,
    quickSale,
    productGrid,
    cart,
    paymentModal,
    cashHistory,
    cashRegister,
    receipt,
    settings,
    configReasonModal,
  } = usePosDashboardController(props);
  const sessions = safeArray(cashHistory.sessions); // [PACK36-pos]

  return (
    <div className="section-grid pos-touch-area" data-testid="pos-page">
      <Toolbar
        title="Venta directa POS"
        subtitle="Busca dispositivos por IMEI, modelo o nombre y controla stock, impuestos y recibos en un solo flujo."
        message={alerts.message}
        error={alerts.error}
      >
        <QuickSaleForm
          stores={quickSale.stores}
          selectedStoreId={quickSale.selectedStoreId}
          onStoreChange={quickSale.onStoreChange}
          search={quickSale.search}
          onSearchChange={quickSale.onSearchChange}
          searchDisabled={quickSale.searchDisabled}
        />
        <ProductGrid
          quickDevices={productGrid.quickDevices}
          filteredDevices={productGrid.filteredDevices}
          disabled={productGrid.disabled}
          onDeviceSelect={productGrid.onDeviceSelect}
        />
      </Toolbar>

      <CartPanel {...cart} />

      <PaymentModal {...paymentModal} />

      <section className="card">
        <h3>Arqueos de caja POS</h3>
        <p className="card-subtitle">
          Controla aperturas, cierres y diferencias por sucursal para cuadrar el efectivo cada
          turno.
        </p>
        <div className="actions-row">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={cashHistory.onRefresh}
            disabled={!quickSale.selectedStoreId || cashHistory.loading}
          >
            Actualizar historial
          </button>
        </div>
        {cashHistory.loading ? (
          <div className="table-wrapper" role="status" aria-busy="true">
            {/* [PACK36-pos] */}
            <Skeleton lines={6} />
          </div>
        ) : sessions.length === 0 ? (
          <p className="muted-text">
            Registra una apertura de caja para iniciar el historial de arqueos de esta sucursal.
          </p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Sesión</th>
                  <th>Estado</th>
                  <th>Apertura</th>
                  <th>Cierre</th>
                  <th>Esperado</th>
                  <th>Diferencia</th>
                  <th>Pagos registrados</th>
                  <th>Abierta</th>
                  <th>Cerrada</th>
                </tr>
              </thead>
              <tbody>
                {sessions.slice(0, 8).map((session) => {
                  const breakdownEntries = Object.entries(session.payment_breakdown ?? {})
                    .filter(([, value]) => Number(value) > 0)
                    .map(
                      ([method, value]) =>
                        `${method}: $${cashHistory.formatCurrency(Number(value))}`,
                    );
                  const breakdownText =
                    breakdownEntries.length > 0 ? breakdownEntries.join(" · ") : "—";
                  const differenceFlag = Math.abs(Number(session.difference_amount ?? 0)) > 0.01;
                  return (
                    <tr key={session.id}>
                      <td>#{session.id}</td>
                      <td>{session.status === "ABIERTO" ? "Abierta" : "Cerrada"}</td>
                      <td>${cashHistory.formatCurrency(Number(session.opening_amount ?? 0))}</td>
                      <td>
                        {session.status === "ABIERTO"
                          ? "—"
                          : `$${cashHistory.formatCurrency(Number(session.closing_amount ?? 0))}`}
                      </td>
                      <td>${cashHistory.formatCurrency(Number(session.expected_amount ?? 0))}</td>
                      <td>
                        ${cashHistory.formatCurrency(Number(session.difference_amount ?? 0))}
                        {differenceFlag ? " ⚠️" : ""}
                      </td>
                      <td>{breakdownText}</td>
                      <td>{cashHistory.formatDateTime(session.opened_at)}</td>
                      <td>{cashHistory.formatDateTime(session.closed_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <CashRegisterModule
        session={cashRegister.session}
        entries={cashRegister.entries}
        loading={cashRegister.loading}
        error={cashRegister.error}
        denominations={cashRegister.denominations}
        onDenominationChange={cashRegister.onDenominationChange}
        reconciliationNotes={cashRegister.reconciliationNotes}
        onReconciliationNotesChange={cashRegister.onReconciliationNotesChange}
        differenceReason={cashRegister.differenceReason}
        onDifferenceReasonChange={cashRegister.onDifferenceReasonChange}
        onRegisterEntry={cashRegister.onRegisterEntry}
        onRefreshEntries={cashRegister.onRefreshEntries}
        onDownloadReport={cashRegister.onDownloadReport}
      />

      <ReceiptPreview token={props.token} sale={receipt.sale} receiptUrl={receipt.receiptUrl} />

      <POSSettings
        config={settings.config}
        devices={settings.devices}
        onSave={settings.onSave}
        onTestPrinter={settings.onTestPrinter}
        onOpenDrawer={settings.onOpenDrawer}
        onDisplayPreview={settings.onDisplayPreview}
        loading={settings.loading}
      />

      <Modal
        open={configReasonModal.open}
        title="Registrar motivo corporativo"
        description="Antes de guardar los cambios del POS captura el motivo corporativo que respalda la actualización."
        onClose={configReasonModal.onClose}
        dismissDisabled={configReasonModal.submitting}
        footer={
          <>
            <Button
              type="button"
              variant="ghost"
              onClick={configReasonModal.onClose}
              disabled={configReasonModal.submitting}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              form="pos-config-reason-form"
              disabled={configReasonModal.submitting}
            >
              {configReasonModal.submitting ? "Guardando…" : "Confirmar motivo"}
            </Button>
          </>
        }
      >
        <form
          id="pos-config-reason-form"
          className="form-grid"
          onSubmit={configReasonModal.onSubmit}
        >
          {configReasonModal.pendingPayload ? (
            <p className="form-span muted-text">
              Se actualizará la configuración de la sucursal #
              {configReasonModal.pendingPayload.store_id}.
            </p>
          ) : null}
          <label className="form-span">
            <span>Motivo corporativo</span>
            <textarea
              value={configReasonModal.reason}
              onChange={(event) => configReasonModal.onReasonChange(event.target.value)}
              minLength={5}
              required
              rows={3}
              placeholder="Describe la razón de negocio para este ajuste"
            />
          </label>
          <p className="form-span muted-text">
            El motivo se almacenará en la bitácora y en el historial corporativo del punto de venta.
          </p>
          {configReasonModal.error ? (
            <p className="form-span alert error">{configReasonModal.error}</p>
          ) : null}
        </form>
      </Modal>
    </div>
  );
}

export default POSDashboard;
