import {
  CustomersFiltersPanel,
  CustomersFormModal,
  CustomersSidePanel,
  CustomersSummaryCards,
  CustomersTable,
  CustomersToolbar,
  CustomersSegmentExports,
} from "./customers";
import {
  CUSTOMER_STATUSES,
  CUSTOMER_TYPES,
  DEBT_FILTERS,
  LEDGER_LABELS,
  useCustomersController,
  type CustomersControllerParams,
} from "./useCustomersController";

type Props = CustomersControllerParams;

function Customers({ token }: Props) {
  const {
    customers,
    customerFilters,
    loadingCustomers,
    savingCustomer,
    error,
    message,
    formState,
    editingId,
    selectedCustomer,
    selectedCustomerId,
    customerSummary,
    summaryLoading,
    summaryError,
    portfolio,
    portfolioFilters,
    portfolioLoading,
    portfolioError,
    exportingPortfolio,
    dashboardMetrics,
    dashboardFilters,
    dashboardLoading,
    dashboardError,
    totalDebt,
    delinquentRatio,
    customerNotes,
    customerHistory,
    recentInvoices,
    formatCurrency,
    resolveDetails,
    handleSubmit,
    handleFormStateChange,
    resetForm,
    handleExportCsv,
    handleCustomerFiltersChange,
    handleSelectCustomer,
    handleEdit,
    handleAddNote,
    handleRegisterPayment,
    handleAdjustDebt,
    handleDelete,
    handlePortfolioFiltersChange,
    refreshPortfolio,
    handleExportPortfolio,
    handleDashboardFiltersChange,
    refreshDashboard,
    customerSegmentExports,
    handleExportSegment,
    exportingSegment,
  } = useCustomersController({ token });

  const customerList = Array.isArray(customers) ? customers : [];
  const notesList = Array.isArray(customerNotes) ? customerNotes : [];
  const historyList = Array.isArray(customerHistory) ? customerHistory : [];
  const invoicesList = Array.isArray(recentInvoices) ? recentInvoices : [];

  return (
    <section className="customers-module">
      <CustomersToolbar
        error={error}
        message={message}
        extraContent={
          <CustomersSegmentExports
            segments={customerSegmentExports}
            exportingKey={exportingSegment}
            onExport={handleExportSegment}
          />
        }
      />

      <CustomersFormModal
        formState={formState}
        customerTypes={CUSTOMER_TYPES}
        customerStatuses={CUSTOMER_STATUSES}
        savingCustomer={savingCustomer}
        editingId={editingId}
        loadingCustomers={loadingCustomers}
        onSubmit={handleSubmit}
        onFormChange={handleFormStateChange}
        onCancelEdit={resetForm}
        onExportCsv={() => {
          void handleExportCsv();
        }}
      />

      <div className="customers-columns">
        <div className="panel">
          <div className="panel__header">
            <h3>Listado de clientes</h3>
            <p className="panel__subtitle">
              Usa filtros combinados para ubicar clientes morosos, VIP o corporativos en segundos.
            </p>
          </div>
          <CustomersFiltersPanel
            filters={customerFilters}
            statuses={CUSTOMER_STATUSES}
            types={CUSTOMER_TYPES}
            debtOptions={DEBT_FILTERS}
            customersCount={customerList.length}
            totalDebt={totalDebt}
            onFilterChange={handleCustomerFiltersChange}
            formatCurrency={formatCurrency}
          />
          <CustomersTable
            customers={customerList}
            loading={loadingCustomers}
            selectedCustomerId={selectedCustomerId}
            formatCurrency={formatCurrency}
            onSelect={handleSelectCustomer}
            onEdit={handleEdit}
            onAddNote={(customer) => {
              void handleAddNote(customer);
            }}
            onRegisterPayment={(customer) => {
              void handleRegisterPayment(customer);
            }}
            onAdjustDebt={(customer) => {
              void handleAdjustDebt(customer);
            }}
            onDelete={(customer) => {
              void handleDelete(customer);
            }}
          />
        </div>

        <CustomersSidePanel
          selectedCustomer={selectedCustomer}
          summary={customerSummary}
          summaryLoading={summaryLoading}
          summaryError={summaryError}
          customerHistory={historyList}
          customerNotes={notesList}
          recentInvoices={invoicesList}
          ledgerLabels={LEDGER_LABELS}
          resolveDetails={resolveDetails}
          formatCurrency={formatCurrency}
        />
      </div>

      <CustomersSummaryCards
        portfolio={portfolio}
        portfolioLoading={portfolioLoading}
        portfolioError={portfolioError}
        portfolioFilters={portfolioFilters}
        dashboardMetrics={dashboardMetrics}
        dashboardLoading={dashboardLoading}
        dashboardError={dashboardError}
        dashboardFilters={dashboardFilters}
        delinquentRatio={delinquentRatio}
        formatCurrency={formatCurrency}
        onPortfolioFiltersChange={handlePortfolioFiltersChange}
        refreshPortfolio={() => {
          void refreshPortfolio();
        }}
        onExportPortfolio={(format) => {
          void handleExportPortfolio(format);
        }}
        onDashboardFiltersChange={handleDashboardFiltersChange}
        refreshDashboard={() => {
          void refreshDashboard();
        }}
        exportingPortfolio={exportingPortfolio}
      />
    </section>
  );
}

export default Customers;
