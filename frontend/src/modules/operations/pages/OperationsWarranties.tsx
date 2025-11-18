import Warranties from "../components/Warranties";
import { useOperationsModule } from "../hooks/useOperationsModule";

export default function OperationsWarranties() {
  const { token, stores, selectedStoreId } = useOperationsModule();

  if (!token || !stores) {
    return (
      <section className="panel">
        <header className="panel__header">
          <h2>Garantías</h2>
        </header>
        <div className="panel__body">
          <p>No se pudo cargar la información de garantías. Verifica tu sesión e intenta nuevamente.</p>
        </div>
      </section>
    );
  }

  return <Warranties token={token} stores={stores} defaultStoreId={selectedStoreId ?? null} />;
}
