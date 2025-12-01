import SalesTable from "./sales/SalesTable";
import SidePanel from "./sales/SidePanel";
import { useSalesLogic } from "./sales/useSalesLogic";

function Sales() {
  const {
    stores,
    customers,
    saleForm,
    handleSaleFormChange,
    deviceQuery,
    setDeviceQuery,
    devices,
    isLoadingDevices,
    handleAddDevice,
    saleItems,
    handleQuantityChange,
    handleBatchCodeChange,
    handleRemoveLine,
    saleSummary,
    paymentLabels,
    isSaving,
    isPrinting,
    handleSubmit,
    handleReset,
    handleRequestInvoice,
    formatCurrency,
    invoiceAvailable,
    sales,
    isLoadingSales,
    salesFilters,
    handleSalesFiltersChange,
  } = useSalesLogic();

  return (
    <div className="sales-layout">
      <div className="sales-panel">
        <SidePanel
          stores={stores}
          customers={customers}
          saleForm={saleForm}
          onSaleFormChange={handleSaleFormChange}
          deviceQuery={deviceQuery}
          onDeviceQueryChange={setDeviceQuery}
          devices={devices}
          isLoadingDevices={isLoadingDevices}
          onAddDevice={handleAddDevice}
          saleItems={saleItems}
          onQuantityChange={handleQuantityChange}
          onBatchCodeChange={handleBatchCodeChange}
          onRemoveLine={handleRemoveLine}
          saleSummary={saleSummary}
          paymentLabels={paymentLabels}
          isSaving={isSaving}
          isPrinting={isPrinting}
          onSubmit={handleSubmit}
          onReset={handleReset}
          onRequestInvoice={handleRequestInvoice}
          formatCurrency={formatCurrency}
          invoiceAvailable={invoiceAvailable}
        />
      </div>

      <div className="sales-list">
        <div className="filters-row">
          <input
            type="date"
            value={salesFilters.dateFrom}
            onChange={(e) =>
              handleSalesFiltersChange({ dateFrom: e.target.value, dateTo: e.target.value })
            }
            className="ui-field"
          />
          <select
            value={salesFilters.storeId ?? ""}
            onChange={(e) =>
              handleSalesFiltersChange({ storeId: e.target.value ? Number(e.target.value) : null })
            }
            className="ui-field"
          >
            <option value="">Todas las sucursales</option>
            {stores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
          <input
            placeholder="Buscar venta..."
            value={salesFilters.query}
            onChange={(e) => handleSalesFiltersChange({ query: e.target.value })}
            className="ui-field"
          />
        </div>

        <SalesTable
          sales={sales}
          isLoading={isLoadingSales}
          formatCurrency={formatCurrency}
          paymentLabels={paymentLabels}
        />
      </div>
    </div>
  );
}

export default Sales;
