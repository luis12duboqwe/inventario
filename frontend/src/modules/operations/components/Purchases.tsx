import {
  PurchasesFiltersPanel,
  PurchasesFormModal,
  PurchasesOrdersPanel,
  PurchasesSidePanel,
  PurchasesSummaryCards,
  PurchasesTable,
  PurchasesToolbar,
} from "./purchases";
import FlowAuditCard, { type FlowAuditFlow } from "../../../shared/components/FlowAuditCard";
import type { PurchaseOrder } from "../../../api";
import {
  usePurchasesController,
  type PurchasesControllerParams,
} from "./usePurchasesController";

const statusLabels: Record<PurchaseOrder["status"], string> = {
  BORRADOR: "Borrador",
  PENDIENTE: "Pendiente",
  APROBADA: "Aprobada",
  ENVIADA: "Enviada",
  PARCIAL: "Recepción parcial",
  COMPLETADA: "Completada",
  CANCELADA: "Cancelada",
};

type Props = PurchasesControllerParams;

function Purchases(props: Props) {
  const {
    form,
    recordForm,
    recordItems,
    recordDevices,
    vendors,
    users,
    statistics,
    recurringOrders,
    orders,
    devices,
    recordFiltersDraft,
    vendorFiltersDraft,
    vendorHistoryFiltersDraft,
    vendorForm,
    editingVendorId,
    selectedVendor,
    vendorHistory,
    vendorSaving,
    vendorExporting,
    vendorsLoading,
    vendorHistoryLoading,
    records,
    recordsLoading,
    statsLoading,
    message,
    error,
    currencyFormatter,
    paymentOptions,
    recordStatusOptions,
    recordSubtotal,
    recordTax,
    recordTotal,
    templateName,
    templateDescription,
    csvLoading,
    templateSaving,
    recurringLoading,
    loading,
    selectedStore,
    handleRecordFiltersDraftChange,
    handleVendorFiltersDraftChange,
    handleVendorHistoryFiltersDraftChange,
    updateForm,
    updateRecordForm,
    updateRecordItem,
    addRecordItem,
    removeRecordItem,
    handleCreate,
    handleRecordSubmit,
    handleRecordFiltersSubmit,
    handleRecordFiltersReset,
    handleExportRecords,
    handleVendorFormSubmit,
    handleVendorInputChange,
    resetVendorForm,
    handleVendorFiltersSubmit,
    handleVendorFiltersReset,
    handleVendorExport,
    handleVendorEdit,
    handleVendorStatusToggle,
    handleVendorHistoryFiltersSubmit,
    handleVendorHistoryFiltersReset,
    handleSelectVendor,
    handleImportCsv,
    setTemplateName,
    setTemplateDescription,
    handleSaveTemplate,
    handleApplyTemplate,
    handleExecuteTemplate,
    getTemplateSupplier,
    handleReceive,
    handleReturn,
    handleCancel,
  } = usePurchasesController(props);

  const auditFlows: FlowAuditFlow[] = [
    {
      id: "ordenes",
      title: "Órdenes y recepciones",
      summary: "Arranca un borrador, agrega dispositivos y confirma la recepción parcial sin salir de la grilla.",
      steps: [
        "Filtra por sucursal o proveedor y limpia filtros con un clic cuando cambies de lote.",
        "Genera el borrador, agrega artículos y aplica la plantilla si existe un acuerdo recurrente.",
        "Recibe parcial o totalmente y sincroniza inventario sin perder el estado del borrador.",
      ],
      actions: [
        {
          id: "ir-ordenes",
          label: "Ir a órdenes",
          tooltip: "Saltar al panel de órdenes y recepciones",
          onClick: () => document.getElementById("purchases-orders-panel")?.scrollIntoView({ behavior: "smooth" }),
        },
        {
          id: "limpiar-filtros-compras",
          label: "Limpiar filtros",
          tooltip: "Reinicia filtros de compras para agilizar la búsqueda",
          onClick: handleRecordFiltersReset,
        },
      ],
    },
    {
      id: "proveedores",
      title: "Proveedores y pagos",
      summary: "Conserva el histórico, exporta y activa/inactiva proveedores con motivo corporativo.",
      steps: [
        "Actualiza datos del proveedor y revisa su historial antes de registrar pagos.",
        "Alterna el estado activo/inactivo y exporta el portafolio con un clic.",
        "Revisa el historial de interacción para decidir si aplicar devoluciones o adelantos.",
      ],
      actions: [
        {
          id: "ir-proveedores",
          label: "Ir a proveedores",
          tooltip: "Desplázate al panel lateral de proveedores",
          onClick: () => document.getElementById("purchases-vendors-panel")?.scrollIntoView({ behavior: "smooth" }),
        },
        {
          id: "reset-proveedores",
          label: "Reiniciar filtros",
          tooltip: "Limpia filtros y mantiene la vista en el panel lateral",
          onClick: () => {
            handleVendorFiltersReset();
            handleVendorHistoryFiltersReset();
          },
        },
      ],
    },
  ];

  return (
    <>
      <PurchasesToolbar
        error={error}
        message={message}
        extraContent={
          <FlowAuditCard
            title="Flujos de compras auditados"
            subtitle="Atajos para registrar órdenes, recepciones y pagos manteniendo el acordeón operativo"
            flows={auditFlows}
          />
        }
      />

      <PurchasesFormModal
        vendors={vendors}
        stores={props.stores}
        devices={recordDevices}
        recordForm={recordForm}
        recordItems={recordItems}
        paymentOptions={paymentOptions}
        recordStatusOptions={recordStatusOptions}
        recordSubtotal={recordSubtotal}
        recordTax={recordTax}
        recordTotal={recordTotal}
        currencyFormatter={currencyFormatter}
        onSubmit={handleRecordSubmit}
        onUpdateRecordForm={updateRecordForm}
        onUpdateRecordItem={updateRecordItem}
        onAddRecordItem={addRecordItem}
        onRemoveRecordItem={removeRecordItem}
      />

      <section className="card" id="purchases-list">
        <h2>Listado general de compras</h2>
        <p className="card-subtitle">
          Consulta todas las compras registradas y filtra por proveedor, fechas o usuario responsable.
        </p>
        <PurchasesFiltersPanel
          filtersDraft={recordFiltersDraft}
          vendors={vendors}
          users={users}
          onFiltersChange={handleRecordFiltersDraftChange}
          onSubmit={handleRecordFiltersSubmit}
          onReset={handleRecordFiltersReset}
          onExport={handleExportRecords}
        />
        <PurchasesTable
          records={records}
          loading={recordsLoading}
          currencyFormatter={currencyFormatter}
        />
      </section>

      <div id="purchases-vendors-panel">
        <PurchasesSidePanel
          vendorForm={vendorForm}
          vendorFiltersDraft={vendorFiltersDraft}
          vendorHistoryFiltersDraft={vendorHistoryFiltersDraft}
          vendors={vendors}
          selectedVendor={selectedVendor}
          vendorHistory={vendorHistory}
          vendorSaving={vendorSaving}
          vendorExporting={vendorExporting}
          vendorsLoading={vendorsLoading}
          vendorHistoryLoading={vendorHistoryLoading}
          editingVendorId={editingVendorId}
          currencyFormatter={currencyFormatter}
          onVendorFormSubmit={handleVendorFormSubmit}
          onVendorInputChange={handleVendorInputChange}
          onVendorFormCancel={resetVendorForm}
          onVendorFiltersSubmit={handleVendorFiltersSubmit}
          onVendorFiltersReset={handleVendorFiltersReset}
          onVendorFiltersChange={handleVendorFiltersDraftChange}
          onVendorExport={handleVendorExport}
          onVendorEdit={handleVendorEdit}
          onVendorSelect={handleSelectVendor}
          onVendorToggleStatus={(vendor) =>
            handleVendorStatusToggle(
              vendor,
              vendor.estado === "activo" ? "inactivo" : "activo",
            )
          }
          onVendorHistoryFiltersSubmit={handleVendorHistoryFiltersSubmit}
          onVendorHistoryFiltersReset={handleVendorHistoryFiltersReset}
          onVendorHistoryFiltersChange={handleVendorHistoryFiltersDraftChange}
        />
      </div>

      <section className="card">
        <h2>Estadísticas de compras</h2>
        <p className="card-subtitle">Visualiza los totales mensuales y los proveedores con mayor participación.</p>
        <PurchasesSummaryCards
          statistics={statistics}
          loading={statsLoading}
          currencyFormatter={currencyFormatter}
        />
      </section>

      <div id="purchases-orders-panel">
        <PurchasesOrdersPanel
          form={form}
          stores={props.stores}
          devices={devices}
          selectedStore={selectedStore}
          templateName={templateName}
          templateDescription={templateDescription}
          csvLoading={csvLoading}
          templateSaving={templateSaving}
          recurringLoading={recurringLoading}
          orders={orders}
          ordersLoading={loading}
          recurringOrders={recurringOrders}
          statusLabels={statusLabels}
          onUpdateForm={updateForm}
          onSubmit={handleCreate}
          onImportCsv={handleImportCsv}
          onTemplateNameChange={setTemplateName}
          onTemplateDescriptionChange={setTemplateDescription}
          onSaveTemplate={handleSaveTemplate}
          onApplyTemplate={handleApplyTemplate}
          onExecuteTemplate={handleExecuteTemplate}
          getTemplateSupplier={getTemplateSupplier}
          onReceive={handleReceive}
          onReturn={handleReturn}
          onCancel={handleCancel}
        />
      </div>
    </>
  );
}

export default Purchases;
