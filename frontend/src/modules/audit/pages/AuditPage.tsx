// [PACK26-AUDIT-PAGE-START]
import { useEffect, useState } from "react";
import { httpGet } from "../../../services/http";
import { apiMap } from "../../../services/sales";
import { useAuthz, PERMS } from "../../../auth/useAuthz";

type Row = { ts:number; userId?:string; module:string; action:string; entityId?:string; meta?:any };

export default function AuditPage(){
  const { can } = useAuthz();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(()=>{
    if (!can(PERMS.AUDIT_VIEW)) return;
    (async ()=>{
      setLoading(true);
      try {
        const url = (apiMap as any).audit?.list ?? "/api/audit/ui";
        const data = await httpGet<{ items: Row[] }>(url, { timeoutMs: 5000 });
        setRows(data?.items || []);
      } catch {
        // fallback: mostrar cola local si no hay backend
        try {
          const local = JSON.parse(localStorage.getItem("sm_ui_audit_queue") || "[]");
          setRows(local);
        } catch {}
      } finally { setLoading(false); }
    })();
  }, [can]);

  if (!can(PERMS.AUDIT_VIEW)) return <div>No autorizado</div>;

  return (
    <div data-testid="audit-page">
      <h2>Auditoría UI</h2>
      {loading ? <div>Cargando…</div> : (
        <table>
          <thead><tr><th>Fecha</th><th>Usuario</th><th>Módulo</th><th>Acción</th><th>Entidad</th><th>Meta</th></tr></thead>
          <tbody>
            {rows.map((r,i)=>(
              <tr key={i}>
                <td>{new Date(r.ts).toLocaleString()}</td>
                <td>{r.userId || "-"}</td>
                <td>{r.module}</td>
                <td>{r.action}</td>
                <td>{r.entityId || "-"}</td>
                <td><pre style={{whiteSpace:"pre-wrap"}}>{JSON.stringify(r.meta||{}, null, 2)}</pre></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
// [PACK26-AUDIT-PAGE-END]
