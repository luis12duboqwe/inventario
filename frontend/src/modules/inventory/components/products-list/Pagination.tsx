import React from "react";
import Button from "../../../../../components/ui/Button";

type Props = {
  page: number;
  pages: number;
  onPage: (page: number) => void;
};

export default function Pagination({ page, pages, onPage }: Props) {
  const prev = () => onPage(Math.max(1, page - 1));
  const next = () => onPage(Math.min(pages, page + 1));

  return (
    <div className="flex justify-center items-center gap-2">
      <Button variant="ghost" size="sm" onClick={prev} disabled={page <= 1}>
        Prev
      </Button>
      <span className="text-sm text-muted-foreground">
        Página {page} de {pages}
      </span>
      <Button variant="ghost" size="sm" onClick={next} disabled={page >= pages}>
        Next
      </Button>
    </div>
  );
}
