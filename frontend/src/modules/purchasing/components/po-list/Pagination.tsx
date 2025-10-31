import React from "react";

type Props = {
  page: number;
  pages: number;
  onPage: (page: number) => void;
};

const containerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  gap: 8,
};

const buttonStyle: React.CSSProperties = {
  padding: "6px 10px",
  borderRadius: 8,
  border: "1px solid rgba(255, 255, 255, 0.08)",
  background: "rgba(37, 99, 235, 0.14)",
  color: "#bfdbfe",
};

export default function Pagination({ page, pages, onPage }: Props) {
  const prev = () => onPage(Math.max(1, page - 1));
  const next = () => onPage(Math.min(pages, page + 1));

  return (
    <div style={containerStyle}>
      <button type="button" onClick={prev} disabled={page <= 1} style={buttonStyle}>
        Prev
      </button>
      <span style={{ fontSize: 12, color: "#94a3b8" }}>
        Página {page} de {pages}
      </span>
      <button type="button" onClick={next} disabled={page >= pages} style={buttonStyle}>
        Next
      </button>
    </div>
  );
}
