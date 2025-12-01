import React, { useState, useEffect, useCallback } from "react";
import { Lock, Unlock } from "lucide-react";
import { useDashboard } from "../../../dashboard/context/DashboardContext";
import { request } from "@api/client";
import { OpenCashSessionModal } from "./OpenCashSessionModal";
import { CloseCashSessionModal } from "./CloseCashSessionModal";

interface CashSession {
  id: number;
  user_id: number;
  store_id: number;
  start_time: string;
  end_time?: string;
  initial_cash: number;
  final_cash?: number;
  status: "open" | "closed";
  total_sales_cash: number;
  total_sales_card: number;
  total_sales_transfer: number;
  discrepancy?: number;
  notes?: string;
}

interface CashRegisterProps {
  storeId: number;
  onSessionChange?: (session: CashSession | null) => void;
}

export const CashRegister: React.FC<CashRegisterProps> = ({ storeId, onSessionChange }) => {
  const dashboard = useDashboard();
  const [currentSession, setCurrentSession] = useState<CashSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [showOpenModal, setShowOpenModal] = useState(false);
  const [showCloseModal, setShowCloseModal] = useState(false);

  const loadCurrentSession = useCallback(async () => {
    setLoading(true);
    try {
      const session = await request<CashSession>(`/pos/sessions/current?store_id=${storeId}`, {
        method: "GET",
        headers: { Authorization: `Bearer ${dashboard.token}` },
      });
      setCurrentSession(session);
      onSessionChange?.(session);
    } catch {
      // No active session is a valid state
      setCurrentSession(null);
      onSessionChange?.(null);
    } finally {
      setLoading(false);
    }
  }, [dashboard.token, onSessionChange, storeId]);

  useEffect(() => {
    if (storeId) {
      void loadCurrentSession();
    }
  }, [storeId, loadCurrentSession]);

  const handleOpenSession = async (initialCash: number, notes: string) => {
    try {
      await request("/pos/sessions/open", {
        method: "POST",
        headers: { Authorization: `Bearer ${dashboard.token}` },
        body: JSON.stringify({
          store_id: storeId,
          initial_cash: initialCash,
          notes,
        }),
      });
      dashboard.pushToast({
        message: "Caja abierta correctamente",
        variant: "success",
      });
      setShowOpenModal(false);
      void loadCurrentSession();
    } catch {
      dashboard.pushToast({
        message: "Error al abrir la caja",
        variant: "error",
      });
    }
  };

  const handleCloseSession = async (finalCash: number, notes: string) => {
    if (!currentSession) return;

    try {
      await request(`/pos/sessions/${currentSession.id}/close`, {
        method: "POST",
        headers: { Authorization: `Bearer ${dashboard.token}` },
        body: JSON.stringify({
          final_cash: finalCash,
          notes,
        }),
      });
      dashboard.pushToast({
        message: "Caja cerrada correctamente",
        variant: "success",
      });
      setShowCloseModal(false);
      void loadCurrentSession();
    } catch {
      dashboard.pushToast({
        message: "Error al cerrar la caja",
        variant: "error",
      });
    }
  };

  if (loading) {
    return <div className="animate-pulse h-12 bg-slate-800 rounded"></div>;
  }

  return (
    <div className="cash-register">
      {currentSession ? (
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
          <div className="flex justify-between items-start mb-4">
            <div>
              <div className="flex items-center gap-2 text-green-400 mb-1">
                <Unlock className="w-5 h-5" />
                <span className="font-semibold">Caja Abierta</span>
              </div>
              <div className="text-sm text-slate-400">
                Iniciada: {new Date(currentSession.start_time).toLocaleString()}
              </div>
            </div>
            <button
              onClick={() => setShowCloseModal(true)}
              className="px-3 py-1 bg-red-600/20 text-red-400 hover:bg-red-600/30 rounded border border-red-600/30 flex items-center gap-2"
            >
              <Lock className="w-4 h-4" />
              Cerrar Caja
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="bg-slate-900/50 p-3 rounded">
              <div className="text-slate-400 mb-1">Fondo Inicial</div>
              <div className="font-mono text-lg">
                ${currentSession.initial_cash.toLocaleString()}
              </div>
            </div>
            <div className="bg-slate-900/50 p-3 rounded">
              <div className="text-slate-400 mb-1">Ventas Efectivo</div>
              <div className="font-mono text-lg text-green-400">
                ${currentSession.total_sales_cash.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-slate-800 p-6 rounded-lg border border-slate-700 text-center">
          <div className="w-12 h-12 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-3 text-slate-400">
            <Lock className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-medium text-white mb-2">Caja Cerrada</h3>
          <p className="text-slate-400 text-sm mb-4">
            Debes abrir caja para comenzar a registrar ventas
          </p>
          <button
            onClick={() => setShowOpenModal(true)}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 flex items-center gap-2 mx-auto"
          >
            <Unlock className="w-4 h-4" />
            Abrir Caja
          </button>
        </div>
      )}

      {showOpenModal && (
        <OpenCashSessionModal
          onClose={() => setShowOpenModal(false)}
          onConfirm={handleOpenSession}
        />
      )}

      {showCloseModal && currentSession && (
        <CloseCashSessionModal
          session={currentSession}
          onClose={() => setShowCloseModal(false)}
          onConfirm={handleCloseSession}
        />
      )}
    </div>
  );
};
