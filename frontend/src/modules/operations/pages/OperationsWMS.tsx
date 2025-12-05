import React, { useEffect, useState } from "react";
import { Box, Map, RefreshCw, Search, ArrowRight } from "lucide-react";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { listWMSBins, WMSBin } from "../../../api/wms";
import { toast } from "sonner";

export default function OperationsWMS(): JSX.Element {
  const { enableWMS } = useDashboard();
  const [bins, setBins] = useState<WMSBin[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (enableWMS) {
      loadData();
    }
  }, [enableWMS]);

  const loadData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token") || "";
      const storeId = Number(localStorage.getItem("store_id") || NaN);

      if (!Number.isFinite(storeId)) {
        throw new Error("storeId no definido");
      }

      const data = await listWMSBins(token, storeId, { limit: 50 });
      setBins(data);
    } catch (error) {
      console.error("Error loading WMS data:", error);
      toast.error("Error al cargar ubicaciones WMS");
    } finally {
      setLoading(false);
    }
  };

  if (!enableWMS) {
    return (
      <section className="operations-disabled">
        <h2 className="operations-disabled__title">
          <Box aria-hidden="true" size={20} />
          Gestión de Almacén (WMS) desactivada
        </h2>
        <p className="operations-disabled__text">
          Define <code>SOFTMOBILE_ENABLE_WMS=1</code> para habilitar la gestión avanzada de
          ubicaciones y racks.
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
              <Box aria-hidden="true" size={20} />
              Gestión de Almacén (WMS)
            </h2>
            <p className="operations-panel__description">
              Administra ubicaciones físicas, racks y asignación de productos en bodega.
            </p>
          </div>
          <button
            onClick={loadData}
            className="ui-button ui-button--ghost"
            disabled={loading}
            aria-label="Actualizar datos"
          >
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
            <div className="p-4 border-b border-slate-700 flex justify-between items-center">
              <h3 className="font-medium text-slate-200 flex items-center gap-2">
                <Map size={18} /> Mapa de Ubicaciones
              </h3>
              <div className="relative">
                <Search
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
                  size={14}
                />
                <input
                  type="text"
                  placeholder="Buscar ubicación..."
                  className="bg-slate-900 border border-slate-700 rounded-md pl-9 pr-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            {loading && bins.length === 0 ? (
              <div className="p-8 text-center text-slate-500">Cargando ubicaciones...</div>
            ) : bins.length === 0 ? (
              <div className="p-8 text-center text-slate-500">No hay ubicaciones definidas.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-800 text-slate-400">
                    <tr>
                      <th className="px-4 py-3 font-medium">Código</th>
                      <th className="px-4 py-3 font-medium">Pasillo</th>
                      <th className="px-4 py-3 font-medium">Rack</th>
                      <th className="px-4 py-3 font-medium">Nivel</th>
                      <th className="px-4 py-3 font-medium">Descripción</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700">
                    {bins.map((bin) => (
                      <tr key={bin.id} className="hover:bg-slate-800/50">
                        <td className="px-4 py-3 font-mono text-cyan-400">{bin.codigo}</td>
                        <td className="px-4 py-3 text-slate-400">{bin.pasillo || "-"}</td>
                        <td className="px-4 py-3 text-slate-400">{bin.rack || "-"}</td>
                        <td className="px-4 py-3 text-slate-400">{bin.nivel || "-"}</td>
                        <td className="px-4 py-3 text-slate-400">{bin.descripcion || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <div>
          <article className="operations-article h-full">
            <h3 className="operations-article__title flex items-center gap-2">
              <Box aria-hidden="true" size={18} />
              Acciones Rápidas
            </h3>
            <div className="space-y-3 mt-4">
              <button className="ui-button ui-button--secondary w-full justify-between group">
                <span>Crear Nueva Ubicación</span>
                <ArrowRight
                  size={16}
                  className="text-slate-500 group-hover:text-cyan-400 transition-colors"
                />
              </button>
              <button className="ui-button ui-button--secondary w-full justify-between group">
                <span>Asignar Productos</span>
                <ArrowRight
                  size={16}
                  className="text-slate-500 group-hover:text-cyan-400 transition-colors"
                />
              </button>
              <button className="ui-button ui-button--secondary w-full justify-between group">
                <span>Auditoría de Ubicaciones</span>
                <ArrowRight
                  size={16}
                  className="text-slate-500 group-hover:text-cyan-400 transition-colors"
                />
              </button>

              <div className="mt-6 pt-6 border-t border-slate-700">
                <h4 className="text-sm font-medium text-slate-300 mb-3">Estadísticas</h4>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Ocupación Global</span>
                    <span className="text-slate-200">0%</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-1.5">
                    <div className="bg-cyan-500 h-1.5 rounded-full" style={{ width: "0%" }}></div>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
