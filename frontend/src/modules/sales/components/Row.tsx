// [PACK25-MEMO-ROW-START]
import React from "react";
type Props = { cells: React.ReactNode[]; onClick?: ()=>void };
function RowBase({ cells, onClick }: Props){
  return (
    <div onClick={onClick} style={{display:"grid", gridTemplateColumns:`repeat(${cells.length},1fr)`, gap:8, padding:"8px 12px"}}>
      {cells.map((c,i)=>(<div key={i}>{c}</div>))}
    </div>
  );
}
export const Row = React.memo(RowBase);
// [PACK25-MEMO-ROW-END]
