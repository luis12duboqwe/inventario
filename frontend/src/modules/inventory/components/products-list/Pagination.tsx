import React from "react";

type Props = {
  page: number;
  pages: number;
  onPage: (page: number) => void;
};

export default function Pagination({ page, pages, onPage }: Props) {
  const prev = () => onPage(Math.max(1, page - 1));
  const next = () => onPage(Math.min(pages, page + 1));

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 8 }}>
      <button onClick={prev} disabled={page <= 1} style={{ padding: "6px 10px", borderRadius: 8 }}>
        Prev
      </button>
      <span style={{ fontSize: 12, color: "#94a3b8" }}>
        Página {page} de {pages}
      </span>
      <button onClick={next} disabled={page >= pages} style={{ padding: "6px 10px", borderRadius: 8 }}>
        Next
      </button>
    </div>
  );
}
