import HardwareDiagnostics from "../components/HardwareDiagnostics";
import { useOperationsModule } from "../hooks/useOperationsModule";

export default function OperationsDiagnostics() {
  const { token, stores, selectedStoreId } = useOperationsModule();

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div>
        <h2 style={{ margin: 0 }}>Diagnósticos</h2>
        <p style={{ margin: 0, color: "#94a3b8" }}>
          Utilidades de hardware para pruebas rápidas en sucursales, sin interrumpir la operación diaria.
        </p>
      </div>
      <HardwareDiagnostics token={token} stores={stores} defaultStoreId={selectedStoreId} />
    </div>
  );
}
