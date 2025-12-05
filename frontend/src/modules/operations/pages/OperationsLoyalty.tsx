import React, { useEffect, useState } from "react";
import { Heart, Gift, Award, Search, RefreshCw } from "lucide-react";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import {
  listLoyaltyAccounts,
  getLoyaltySummary,
  LoyaltyAccount,
  LoyaltyReportSummary,
} from "../../../api/loyalty";
import { toast } from "sonner";

export default function OperationsLoyalty(): JSX.Element {
  const { enableLoyalty } = useDashboard();
  const [accounts, setAccounts] = useState<LoyaltyAccount[]>([]);
  const [summary, setSummary] = useState<LoyaltyReportSummary | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (enableLoyalty) {
      loadData();
    }
  }, [enableLoyalty]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [accountsData, summaryData] = await Promise.all([
        listLoyaltyAccounts(localStorage.getItem("token") || ""),
        getLoyaltySummary(localStorage.getItem("token") || ""),
      ]);
      setAccounts(accountsData);
      setSummary(summaryData);
    } catch (error) {
      console.error("Error loading loyalty data:", error);
      toast.error("Error al cargar datos de fidelización");
    } finally {
      setLoading(false);
    }
  };

  if (!enableLoyalty) {
    return (
      <section className="operations-disabled">
        <h2 className="operations-disabled__title">
          <Heart aria-hidden="true" size={20} />
          Fidelización desactivada
        </h2>
        <p className="operations-disabled__text">
          Define <code>SOFTMOBILE_ENABLE_LOYALTY=1</code> para habilitar el sistema de puntos y
          recompensas.
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
              <Heart aria-hidden="true" size={20} />
              Fidelización y Puntos
            </h2>
            <p className="operations-panel__description">
              Gestiona cuentas de clientes, acumulación de puntos y canje de recompensas.
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

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
            <div className="text-slate-400 text-sm mb-1">Cuentas Activas</div>
            <div className="text-2xl font-bold text-cyan-400">{summary.active_accounts}</div>
          </div>
          <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
            <div className="text-slate-400 text-sm mb-1">Puntos Circulantes</div>
            <div className="text-2xl font-bold text-emerald-400">
              {summary.total_balance.toLocaleString()}
            </div>
          </div>
          <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
            <div className="text-slate-400 text-sm mb-1">Puntos Canjeados</div>
            <div className="text-2xl font-bold text-amber-400">
              {summary.total_redeemed.toLocaleString()}
            </div>
          </div>
          <div className="p-4 bg-slate-800 rounded-lg border border-slate-700">
            <div className="text-slate-400 text-sm mb-1">Puntos Expirados</div>
            <div className="text-2xl font-bold text-rose-400">
              {summary.total_expired.toLocaleString()}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
            <div className="p-4 border-b border-slate-700 flex justify-between items-center">
              <h3 className="font-medium text-slate-200 flex items-center gap-2">
                <Award size={18} /> Cuentas Recientes
              </h3>
              <div className="relative">
                <Search
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
                  size={14}
                />
                <input
                  type="text"
                  placeholder="Buscar cliente..."
                  className="bg-slate-900 border border-slate-700 rounded-md pl-9 pr-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            {loading && accounts.length === 0 ? (
              <div className="p-8 text-center text-slate-500">Cargando cuentas...</div>
            ) : accounts.length === 0 ? (
              <div className="p-8 text-center text-slate-500">
                No hay cuentas de fidelización registradas.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-800 text-slate-400">
                    <tr>
                      <th className="px-4 py-3 font-medium">Cliente ID</th>
                      <th className="px-4 py-3 font-medium text-right">Puntos</th>
                      <th className="px-4 py-3 font-medium text-right">Acumulados</th>
                      <th className="px-4 py-3 font-medium text-right">Canjeados</th>
                      <th className="px-4 py-3 font-medium">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700">
                    {accounts.map((account) => (
                      <tr key={account.id} className="hover:bg-slate-800/50">
                        <td className="px-4 py-3 text-slate-300">#{account.customer_id}</td>
                        <td className="px-4 py-3 text-right font-mono text-cyan-400 font-medium">
                          {account.balance_points}
                        </td>
                        <td className="px-4 py-3 text-right text-slate-400">
                          {account.lifetime_points_earned}
                        </td>
                        <td className="px-4 py-3 text-right text-slate-400">
                          {account.lifetime_points_redeemed}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                              account.is_active
                                ? "bg-emerald-500/10 text-emerald-400"
                                : "bg-slate-700 text-slate-400"
                            }`}
                          >
                            {account.is_active ? "Activo" : "Inactivo"}
                          </span>
                        </td>
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
              <Gift aria-hidden="true" size={18} />
              Configuración Rápida
            </h3>
            <div className="space-y-4 mt-4">
              <div className="p-3 bg-slate-800 rounded-lg border border-slate-700">
                <div className="text-xs text-slate-400 mb-1">Tasa de Acumulación</div>
                <div className="font-medium text-slate-200">1 punto por cada $100</div>
              </div>
              <div className="p-3 bg-slate-800 rounded-lg border border-slate-700">
                <div className="text-xs text-slate-400 mb-1">Valor del Punto</div>
                <div className="font-medium text-slate-200">$1 peso (Canje)</div>
              </div>
              <div className="p-3 bg-slate-800 rounded-lg border border-slate-700">
                <div className="text-xs text-slate-400 mb-1">Vencimiento</div>
                <div className="font-medium text-slate-200">365 días</div>
              </div>

              <button className="ui-button ui-button--secondary w-full mt-2">Ajustar Reglas</button>
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
