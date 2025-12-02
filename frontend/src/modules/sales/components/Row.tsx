// [PACK25-MEMO-ROW-START]
import React from "react";
type Props = { cells: React.ReactNode[]; onClick?: () => void };
function RowBase({ cells, onClick }: Props) {
  return (
    <div
      role="row"
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={(e) => {
        if (onClick && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onClick();
        }
      }}
      className="sales-row"
      style={{ "--sales-row-cols": cells.length } as React.CSSProperties}
    >
      {cells.map((c, i) => (
        <div key={i} role="cell">
          {c}
        </div>
      ))}
    </div>
  );
}
export const Row = React.memo(RowBase);
// [PACK25-MEMO-ROW-END]
