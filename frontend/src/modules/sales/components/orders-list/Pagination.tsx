import React from "react";

export type OrdersPaginationProps = {
  page: number;
  pages: number;
  onPage: (page: number) => void;
};

function Pagination({ page, pages, onPage }: OrdersPaginationProps) {
  const handlePrev = () => onPage(Math.max(1, page - 1));
  const handleNext = () => onPage(Math.min(pages, page + 1));

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 8 }}>
      <button onClick={handlePrev} disabled={page <= 1} style={{ padding: "6px 10px", borderRadius: 8 }}>
        Anterior
      </button>
      <span style={{ fontSize: 12, color: "#94a3b8" }}>
        Página {page} de {pages}
      </span>
      <button onClick={handleNext} disabled={page >= pages} style={{ padding: "6px 10px", borderRadius: 8 }}>
        Siguiente
      </button>
    </div>
  );
}

export default Pagination;
