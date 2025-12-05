import { useState, useRef, useCallback } from "react";
import { Maximize, Minimize } from "lucide-react";
import SalesTable from "./sales/SalesTable";
import SidePanel from "./sales/SidePanel";
import { useSalesLogic } from "./sales/useSalesLogic";
import { useHotkeys } from "../../../hooks/useHotkeys";
import { useSoundFeedback } from "../../../hooks/useSoundFeedback";
import "./Sales.css";

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

  const [isFullScreen, setIsFullScreen] = useState(false);
  const deviceSearchRef = useRef<HTMLInputElement>(null);
  const customerSelectRef = useRef<HTMLSelectElement>(null);
  const { playSound } = useSoundFeedback();

  const toggleFullScreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement
        .requestFullscreen()
        .then(() => {
          setIsFullScreen(true);
        })
        .catch((err) => {
          console.error(
            `Error attempting to enable full-screen mode: ${err.message} (${err.name})`,
          );
        });
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
        setIsFullScreen(false);
      }
    }
  }, []);

  // Hotkeys
  useHotkeys(
    "F2",
    () => {
      playSound("beep");
      deviceSearchRef.current?.focus();
    },
    [playSound],
  );

  useHotkeys(
    "F3",
    () => {
      playSound("beep");
      customerSelectRef.current?.focus();
    },
    [playSound],
  );

  useHotkeys(
    "F11",
    (e) => {
      e.preventDefault();
      toggleFullScreen();
    },
    [toggleFullScreen],
  );

  useHotkeys(
    "F12",
    (e) => {
      e.preventDefault();
      playSound("success");
      // Trigger submit programmatically
      const mockEvent = { preventDefault: () => {} } as React.FormEvent<HTMLFormElement>;
      handleSubmit(mockEvent);
    },
    [handleSubmit, playSound],
  );

  useHotkeys(
    "Escape",
    () => {
      playSound("click");
      handleReset();
    },
    [handleReset, playSound],
  );

  const handleSubmitWithSound = (e: React.FormEvent<HTMLFormElement>) => {
    playSound("success");
    handleSubmit(e);
  };

  return (
    <div className={`sales-layout ${isFullScreen ? "sales-layout--fullscreen" : ""}`}>
      <div className="sales-panel">
        <div className="sales-panel__header-actions flex justify-end mb-2 gap-2">
          <div className="text-xs text-text-secondary flex items-center gap-3 mr-auto">
            <span className="hidden md:inline">F2: Buscar producto</span>
            <span className="hidden md:inline">F3: Cliente</span>
            <span className="hidden md:inline">F12: Cobrar</span>
            <span className="hidden md:inline">ESC: Cancelar</span>
          </div>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={toggleFullScreen}
            title="Alternar pantalla completa (F11)"
          >
            {isFullScreen ? <Minimize size={16} /> : <Maximize size={16} />}
          </button>
        </div>
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
          onSubmit={handleSubmitWithSound}
          onReset={handleReset}
          onRequestInvoice={handleRequestInvoice}
          formatCurrency={formatCurrency}
          invoiceAvailable={invoiceAvailable}
          deviceSearchRef={deviceSearchRef}
          customerSelectRef={customerSelectRef}
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
