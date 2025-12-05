import React, { useState, useEffect, useCallback } from "react";
import { Calendar, CheckCircle, AlertCircle, Clock, FileText } from "lucide-react";
import { useDashboard } from "../../../dashboard/context/DashboardContext";
import { emitClientError } from "../../../../utils/clientLog";
import { request } from "@api/client";
import { CustomerDebtSnapshot, CreditScheduleEntry, CustomerPaymentReceipt } from "@api/customers";

interface CreditInstallment {
  id: number;
  sale_id: number;
  due_date: string;
  amount: number;
  status: "pending" | "paid" | "overdue";
  paid_at?: string;
  notes?: string;
}

interface CreditScheduleProps {
  saleId?: number;
  totalAmount?: number;
  onScheduleCreated?: () => void;
  debtSummary?: CustomerDebtSnapshot | null;
  schedule?: CreditScheduleEntry[];
  debtReceiptBase64?: string | null;
  paymentReceipts?: CustomerPaymentReceipt[];
}
export const CreditSchedule: React.FC<CreditScheduleProps> = ({
  saleId,
  totalAmount,
  onScheduleCreated,
  debtSummary,
  schedule,
  debtReceiptBase64,
  paymentReceipts,
}) => {
  const dashboard = useDashboard();
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [installments, setInstallments] = useState<CreditInstallment[]>([]);
  const [config, setConfig] = useState({
    count: 3,
    frequency: "monthly" as "weekly" | "biweekly" | "monthly",
    firstDate: new Date().toISOString().split("T")[0],
  });

  const loadSchedule = useCallback(async () => {
    if (!saleId) return;
    setLoading(true);
    try {
      const data = await request<CreditInstallment[]>(`/sales/${saleId}/installments`, {
        method: "GET",
        headers: { Authorization: `Bearer ${dashboard.token}` },
      });
      setInstallments(data);
    } catch (error) {
      emitClientError("Error loading installments:", error);
    } finally {
      setLoading(false);
    }
  }, [saleId, dashboard.token]);

  useEffect(() => {
    if (schedule && schedule.length > 0) {
      const mapped = schedule.map(
        (entry, index) =>
          ({
            id: index,
            sale_id: saleId ?? 0,
            due_date: entry.due_date,
            amount: entry.amount,
            status: entry.status === "due_soon" ? "pending" : entry.status,
          } as CreditInstallment),
      );
      setInstallments(mapped);
    } else if (saleId) {
      void loadSchedule();
    }
  }, [saleId, schedule, loadSchedule]);

  const generateSchedule = async () => {
    if (!saleId || !totalAmount) return;
    setLoading(true);
    try {
      await request(`/sales/${saleId}/installments/generate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${dashboard.token}` },
        body: JSON.stringify({
          total_amount: totalAmount,
          installments_count: config.count,
          frequency: config.frequency,
          first_due_date: config.firstDate,
        }),
      });
      dashboard.pushToast({
        message: "Plan de pagos generado correctamente",
        variant: "success",
      });
      setShowForm(false);
      void loadSchedule();
      onScheduleCreated?.();
    } catch (error) {
      emitClientError("Error generating credit schedule:", error);
      dashboard.pushToast({
        message: "Error al generar el plan de pagos",
        variant: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const markAsPaid = async (installmentId: number) => {
    if (!saleId) return;
    if (!window.confirm("¿Confirmar pago de esta cuota?")) return;

    try {
      await request(`/sales/installments/${installmentId}/pay`, {
        method: "POST",
        headers: { Authorization: `Bearer ${dashboard.token}` },
      });
      dashboard.pushToast({
        message: "Cuota marcada como pagada",
        variant: "success",
      });
      await loadSchedule();
    } catch (error) {
      emitClientError("Error marking installment as paid:", error);
      dashboard.pushToast({
        message: "Error al registrar el pago",
        variant: "error",
      });
    }
  };

  const handleDownloadReceipt = () => {
    if (debtReceiptBase64) {
      const link = document.createElement("a");
      link.href = `data:application/pdf;base64,${debtReceiptBase64}`;
      link.download = `recibo_credito_${saleId || "venta"}.pdf`;
      link.click();
    }
  };

  const handleDownloadPaymentReceipt = (receipt: CustomerPaymentReceipt, index: number) => {
    if (receipt.receipt_pdf_base64) {
      const link = document.createElement("a");
      link.href = `data:application/pdf;base64,${receipt.receipt_pdf_base64}`;
      link.download = `recibo_pago_${saleId || "venta"}_${index + 1}.pdf`;
      link.click();
    }
  };

  if (loading && !installments.length) {
    return <div className="p-4 text-center">Cargando plan de pagos...</div>;
  }

  const renderDebtSummary = () => {
    if (!debtSummary) return null;
    return (
      <div className="bg-slate-900 p-3 rounded border border-slate-700 mb-4">
        <h4 className="text-sm font-semibold text-slate-300 mb-2">Resumen de Deuda</h4>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-slate-400">Saldo Anterior:</div>
          <div className="text-right">${debtSummary.previous_balance.toLocaleString()}</div>
          <div className="text-slate-400">Nuevos Cargos:</div>
          <div className="text-right text-blue-400">
            +${debtSummary.new_charges.toLocaleString()}
          </div>
          <div className="text-slate-400">Pagos Aplicados:</div>
          <div className="text-right text-green-400">
            -${debtSummary.payments_applied.toLocaleString()}
          </div>
          <div className="text-slate-200 font-bold border-t border-slate-700 pt-1 mt-1">
            Saldo Final:
          </div>
          <div className="text-right font-bold text-white border-t border-slate-700 pt-1 mt-1">
            ${debtSummary.remaining_balance.toLocaleString()}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="credit-schedule">
      {renderDebtSummary()}

      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Calendar className="w-5 h-5" />
          Plan de Pagos
        </h3>
        {debtReceiptBase64 && (
          <button
            onClick={handleDownloadReceipt}
            className="px-3 py-1 bg-slate-700 text-white rounded hover:bg-slate-600 text-sm flex items-center gap-1"
          >
            <FileText className="w-4 h-4" /> Recibo Crédito
          </button>
        )}
        {paymentReceipts?.map((receipt, index) => (
          <button
            key={index}
            onClick={() => handleDownloadPaymentReceipt(receipt, index)}
            className="px-3 py-1 bg-green-700 text-white rounded hover:bg-green-600 text-sm flex items-center gap-1"
          >
            <FileText className="w-4 h-4" /> Recibo Pago {index + 1}
          </button>
        ))}
        {!installments.length && !showForm && saleId && totalAmount && (
          <button
            onClick={() => setShowForm(true)}
            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
          >
            Generar Plan
          </button>
        )}
      </div>

      {showForm && (
        <div className="bg-slate-800 p-4 rounded-lg mb-4 border border-slate-700">
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label htmlFor="installments-count" className="block text-sm text-slate-400 mb-1">
                Cuotas
              </label>
              <input
                id="installments-count"
                type="number"
                min="1"
                max="24"
                value={config.count}
                onChange={(e) => setConfig({ ...config, count: parseInt(e.target.value) })}
                className="w-full bg-slate-900 border-slate-700 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label htmlFor="installments-frequency" className="block text-sm text-slate-400 mb-1">
                Frecuencia
              </label>
              <select
                id="installments-frequency"
                value={config.frequency}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    frequency: e.target.value as "weekly" | "biweekly" | "monthly",
                  })
                }
                className="w-full bg-slate-900 border-slate-700 rounded px-3 py-2 text-white"
              >
                <option value="weekly">Semanal</option>
                <option value="biweekly">Quincenal</option>
                <option value="monthly">Mensual</option>
              </select>
            </div>
            <div className="col-span-2">
              <label htmlFor="first-due-date" className="block text-sm text-slate-400 mb-1">
                Primer Vencimiento
              </label>
              <input
                id="first-due-date"
                type="date"
                value={config.firstDate}
                onChange={(e) => setConfig({ ...config, firstDate: e.target.value })}
                className="w-full bg-slate-900 border-slate-700 rounded px-3 py-2 text-white"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowForm(false)}
              className="px-3 py-1 text-slate-400 hover:text-white"
            >
              Cancelar
            </button>
            <button
              onClick={() => void generateSchedule()}
              disabled={loading}
              className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Generar
            </button>
          </div>
        </div>
      )}

      {installments.length > 0 ? (
        <div className="space-y-2">
          {installments.map((inst, index) => (
            <div
              key={inst.id || index}
              className={`flex justify-between items-center p-3 rounded border ${
                inst.status === "paid"
                  ? "bg-green-900/20 border-green-800"
                  : inst.status === "overdue"
                  ? "bg-red-900/20 border-red-800"
                  : "bg-slate-800 border-slate-700"
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 flex items-center justify-center bg-slate-700 rounded-full text-xs">
                  {index + 1}
                </span>
                <div>
                  <div className="font-medium">${inst.amount.toLocaleString()}</div>
                  <div className="text-xs text-slate-400">
                    Vence: {new Date(inst.due_date).toLocaleDateString()}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {inst.status === "paid" ? (
                  <span className="flex items-center gap-1 text-green-400 text-sm">
                    <CheckCircle className="w-4 h-4" /> Pagado
                  </span>
                ) : inst.status === "overdue" ? (
                  <span className="flex items-center gap-1 text-red-400 text-sm">
                    <AlertCircle className="w-4 h-4" /> Vencido
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-blue-400 text-sm">
                    <Clock className="w-4 h-4" /> Pendiente
                  </span>
                )}
                {inst.status !== "paid" && saleId && (
                  <button
                    onClick={() => void markAsPaid(inst.id)}
                    className="p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-white"
                    title="Marcar como pagado"
                  >
                    <CheckCircle className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        !showForm && (
          <div className="text-center py-8 text-slate-500 border-2 border-dashed border-slate-800 rounded-lg">
            {saleId ? "No hay plan de pagos configurado" : "No hay información de crédito"}
          </div>
        )
      )}
    </div>
  );
};
