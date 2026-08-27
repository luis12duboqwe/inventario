import { useCallback, useEffect, useState } from "react";
import {
  FileDigit,
  ShieldCheck,
  RefreshCw,
  FileText,
  AlertTriangle,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { listDTEAuthorizations, type DTEAuthorization } from "../../../api/dte";
import { toast } from "sonner";

export default function OperationsDte(): JSX.Element {
  const { enableDte, enableTwoFactor, token, selectedStoreId } = useDashboard();
  const [authorizations, setAuthorizations] = useState<DTEAuthorization[]>([]);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    if (!token) {
      setAuthorizations([]);
      return;
    }

    setLoading(true);
    try {
      const params = selectedStoreId ? { store_id: selectedStoreId } : {};
      const auths = await listDTEAuthorizations(token, params);
      setAuthorizations(auths);
    } catch (error) {
      console.error("Error loading DTE data:", error);
      toast.error("Error al cargar datos de DTE");
    } finally {
      setLoading(false);
    }
  }, [selectedStoreId, token]);

  useEffect(() => {
    if (enableDte) {
      void loadData();
    }
  }, [enableDte, loadData]);

  const handleGenerationHelp = () => {
    toast.info("Genera el DTE desde una venta registrada para conservar la trazabilidad fiscal.");
  };

  if (!enableDte) {
    return (
      <section className="operations-disabled">
        <h2 className="operations-disabled__title">
          <FileDigit aria-hidden="true" size={20} />
          Documentos electrónicos desactivados
        </h2>
        <p className="operations-disabled__text">
          Define <code>SOFTMOBILE_ENABLE_DTE=1</code> junto con{" "}
          <code>SOFTMOBILE_ENABLE_PURCHASES_SALES=1</code> para emitir comprobantes electrónicos
          desde el POS y las ventas corporativas.
        </p>
      </section>
    );
  }

  return (
    <section className="operations-panel">
      <header className="operations-panel__header">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="operations-panel__title">
              <FileDigit aria-hidden="true" size={20} />
              Gestión de DTE
            </h2>
            <p className="operations-panel__description">
              Administración de folios, secuencias y documentos tributarios electrónicos.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadData()}
            className="ui-button ui-button--ghost"
            disabled={loading}
            aria-label="Actualizar datos"
          >
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <article className="operations-article">
          <h3 className="operations-article__title flex items-center gap-2">
            <ShieldCheck aria-hidden="true" size={18} />
            Autorizaciones (CAF)
          </h3>

          {loading ? (
            <div className="p-4 text-center text-gray-400">Cargando autorizaciones...</div>
          ) : authorizations.length === 0 ? (
            <div className="p-4 text-center text-gray-400 bg-slate-800/30 rounded-lg border border-slate-700 border-dashed">
              No hay archivos CAF cargados para la sucursal seleccionada.
            </div>
          ) : (
            <div className="space-y-3 mt-4">
              {authorizations.map((auth) => (
                <div
                  key={auth.id}
                  className="p-3 bg-slate-800 rounded-lg border border-slate-700 flex justify-between items-center"
                >
                  <div>
                    <div className="font-medium text-slate-200">Tipo DTE: {auth.document_type}</div>
                    <div className="text-xs text-slate-400">
                      Rango: {auth.range_start} - {auth.range_end}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-mono text-cyan-400">Disp: {auth.remaining}</div>
                    <div className="text-xs text-slate-500">
                      Vence: {new Date(auth.expiration_date).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="mt-4 pt-4 border-t border-slate-700">
            <button type="button" className="ui-button ui-button--secondary w-full text-sm">
              Cargar nuevo CAF
            </button>
          </div>
        </article>

        <article className="operations-article">
          <h3 className="operations-article__title flex items-center gap-2">
            <FileText aria-hidden="true" size={18} />
            Operaciones rápidas
          </h3>

          <div className="space-y-4 mt-4">
            <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
              <div className="flex items-start gap-3">
                <AlertTriangle className="text-amber-400 shrink-0 mt-0.5" size={16} />
                <div>
                  <h4 className="text-sm font-medium text-slate-200">Emisión trazable</h4>
                  <p className="text-xs text-slate-400 mt-1">
                    La API actual genera documentos a partir de una venta real. Se retiró el payload
                    de prueba obsoleto para evitar comprobantes sin trazabilidad.
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={handleGenerationHelp}
                className="ui-button ui-button--primary w-full justify-center"
              >
                Cómo generar DTE
              </button>
              <button type="button" className="ui-button ui-button--secondary w-full justify-center">
                Ver historial
              </button>
            </div>

            <div className="text-xs text-slate-500 mt-2 flex items-center gap-2">
              {enableTwoFactor ? (
                <>
                  <CheckCircle size={12} className="text-emerald-400" /> 2FA Activo para firma
                </>
              ) : (
                <>
                  <XCircle size={12} className="text-rose-400" /> 2FA Recomendado
                </>
              )}
            </div>
          </div>
        </article>
      </div>
    </section>
  );
}