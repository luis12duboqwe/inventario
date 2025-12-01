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
    <div className="orders-list-pagination">
      <button onClick={handlePrev} disabled={page <= 1} className="orders-list-pagination-btn">
        Anterior
      </button>
      <span className="orders-list-pagination-info">
        Página {page} de {pages}
      </span>
      <button onClick={handleNext} disabled={page >= pages} className="orders-list-pagination-btn">
        Siguiente
      </button>
    </div>
  );
}

export default Pagination;
