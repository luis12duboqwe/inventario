import HardwareDiagnostics from "../components/HardwareDiagnostics";
import { useOperationsModule } from "../hooks/useOperationsModule";

export default function OperationsDiagnostics() {
  const { token, stores, selectedStoreId } = useOperationsModule();

  return (
    <div className="operations-panel">
      <div>
        <h2 className="operations-panel__title">Diagnósticos</h2>
        <p className="operations-panel__description">
          Utilidades de hardware para pruebas rápidas en sucursales, sin interrumpir la operación
          diaria.
        </p>
      </div>
      <HardwareDiagnostics token={token} stores={stores} defaultStoreId={selectedStoreId} />
    </div>
  );
}
