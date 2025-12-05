import {
  cloneElement,
  isValidElement,
  type ReactElement,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { AnimatePresence, motion } from "framer-motion";

import { useDashboard } from "../../modules/dashboard/context/DashboardContext";

type ScrollableTableProps<T> = {
  items: T[];
  itemKey: (item: T, index: number) => string | number;
  renderHead: () => ReactNode;
  renderRow: (item: T, index: number, absoluteIndex: number) => ReactElement | ReactNode;
  emptyMessage?: ReactNode;
  pageSize?: number;
  maxHeight?: number;
  title?: string;
  ariaLabel?: string;
  footer?: ReactNode;
  tableClassName?: string;
};

function ScrollableTable<T>({
  items,
  itemKey,
  renderHead,
  renderRow,
  emptyMessage,
  pageSize = 25,
  maxHeight = 500,
  title,
  ariaLabel,
  footer,
  tableClassName,
}: ScrollableTableProps<T>) {
  const { compactMode } = useDashboard();
  const [page, setPage] = useState(1);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [fullScreenLimit, setFullScreenLimit] = useState(pageSize);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const overlayViewportRef = useRef<HTMLDivElement | null>(null);

  // Nota: evitamos setState dentro de efectos para reducir renders en cascada.
  // El reinicio de la paginación y del límite en pantalla completa se maneja
  // mediante derivación segura de valores y eventos de usuario.

  useEffect(() => {
    if (!isFullScreen) {
      return;
    }
    const node = sentinelRef.current;
    if (!node) {
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      const isIntersecting = entries.some((entry) => entry.isIntersecting);
      if (isIntersecting) {
        setFullScreenLimit((current) => {
          if (current >= items.length) {
            return current;
          }
          return Math.min(current + pageSize, items.length);
        });
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [isFullScreen, items.length, pageSize]);

  useEffect(() => {
    if (!isFullScreen) {
      return;
    }
    const { current } = overlayViewportRef;
    if (current) {
      current.scrollTo({ top: 0 });
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isFullScreen]);

  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const safePage = Math.min(Math.max(1, page), totalPages);
  const rangeStart = items.length === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const rangeEnd = Math.min(safePage * pageSize, items.length);

  const pagedItems = useMemo(() => {
    const start = (safePage - 1) * pageSize;
    return items.slice(start, start + pageSize);
  }, [items, safePage, pageSize]);

  const fullScreenItems = useMemo(() => items.slice(0, fullScreenLimit), [items, fullScreenLimit]);

  const renderRows = (data: T[], startIndex: number) =>
    data.map((item, index) => {
      const content = renderRow(item, index, startIndex + index);
      const key = itemKey(item, startIndex + index);
      if (isValidElement(content)) {
        return cloneElement(content, {
          key,
        });
      }
      return <tr key={key}>{content}</tr>;
    });

  if (items.length === 0) {
    return <div className="scrollable-table__empty">{emptyMessage ?? "Sin registros"}</div>;
  }

  return (
    <div className={`scrollable-table${compactMode ? " compact" : ""}`}>
      <div className="scrollable-table__controls">
        <span className="scrollable-table__summary">
          Mostrando {rangeStart} – {rangeEnd} de {items.length} registros
        </span>
        <div className="scrollable-table__actions">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => {
              // Al abrir pantalla completa, reestablece el límite al tamaño de página actual
              setFullScreenLimit(pageSize);
              setIsFullScreen(true);
            }}
          >
            Expandir vista completa
          </button>
        </div>
      </div>
      <div
        className="scrollable-table__viewport"
        style={{ maxHeight: `${maxHeight}px` }}
        role="region"
        aria-label={ariaLabel}
      >
        <table className={tableClassName}>
          <thead>
            <tr>{renderHead()}</tr>
          </thead>
          <tbody>{renderRows(pagedItems, (page - 1) * pageSize)}</tbody>
        </table>
      </div>
      <div className="scrollable-table__pagination" role="navigation" aria-label="Paginación">
        <button
          type="button"
          onClick={() => setPage(1)}
          disabled={page === 1}
          className="btn btn--ghost"
        >
          « Primero
        </button>
        <button
          type="button"
          onClick={() => setPage((current) => Math.max(1, current - 1))}
          disabled={page === 1}
          className="btn btn--ghost"
        >
          ‹ Anterior
        </button>
        <span className="scrollable-table__page-indicator">
          Página {safePage} de {totalPages}
        </span>
        <button
          type="button"
          onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
          disabled={safePage === totalPages}
          className="btn btn--ghost"
        >
          Siguiente ›
        </button>
        <button
          type="button"
          onClick={() => setPage(totalPages)}
          disabled={safePage === totalPages}
          className="btn btn--ghost"
        >
          Último »
        </button>
      </div>
      {footer ? <div className="scrollable-table__footer">{footer}</div> : null}
      <AnimatePresence>
        {isFullScreen ? (
          <motion.div
            key="scrollable-table-overlay"
            className="scrollable-table__overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="scrollable-table__overlay-content"
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.96, opacity: 0 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              role="dialog"
              aria-modal="true"
              aria-label={title ?? "Vista completa"}
            >
              <header className="scrollable-table__overlay-header">
                <div>
                  <h2>{title ?? "Vista completa"}</h2>
                  <p className="muted-text">
                    Desplázate para explorar todos los registros. La vista carga datos adicionales
                    automáticamente.
                  </p>
                </div>
                <button type="button" className="btn" onClick={() => setIsFullScreen(false)}>
                  Volver a vista normal
                </button>
              </header>
              <div className="scrollable-table__overlay-viewport" ref={overlayViewportRef}>
                <table className={tableClassName}>
                  <thead>
                    <tr>{renderHead()}</tr>
                  </thead>
                  <tbody>{renderRows(fullScreenItems, 0)}</tbody>
                </table>
                <div ref={sentinelRef} aria-hidden="true" className="scrollable-table__sentinel">
                  {fullScreenLimit < items.length
                    ? "Cargando más registros…"
                    : "Todos los registros cargados"}
                </div>
              </div>
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

export default ScrollableTable;
