import {
  PurchasesFiltersPanel,
  PurchasesFormModal,
  PurchasesOrdersPanel,
  PurchasesSidePanel,
  PurchasesSummaryCards,
  PurchasesTable,
  PurchasesToolbar,
} from "./purchases";
import type { PurchaseOrder } from "../../../api";
import {
  usePurchasesController,
  type PurchasesControllerParams,
} from "./usePurchasesController";

const statusLabels: Record<PurchaseOrder["status"], string> = {
  PENDIENTE: "Pendiente",
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

  return (
    <>
      <PurchasesToolbar error={error} message={message} />

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

      <section className="card">
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
        onVendorToggleStatus={handleVendorStatusToggle}
        onVendorHistoryFiltersSubmit={handleVendorHistoryFiltersSubmit}
        onVendorHistoryFiltersReset={handleVendorHistoryFiltersReset}
        onVendorHistoryFiltersChange={handleVendorHistoryFiltersDraftChange}
      />

      <section className="card">
        <h2>Estadísticas de compras</h2>
        <p className="card-subtitle">Visualiza los totales mensuales y los proveedores con mayor participación.</p>
        <PurchasesSummaryCards
          statistics={statistics}
          loading={statsLoading}
          currencyFormatter={currencyFormatter}
        />
      </section>

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
    </>
  );
}

export default Purchases;
