/* eslint-disable react-hooks/exhaustive-deps */
import React, { ReactNode, useCallback, useEffect, useMemo, useState } from "react";

export type ToolbarAction = {
  id: string;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  title?: string;
};

export type PageToolbarProps = {
  /** Nodo con filtros avanzados (chips, selects, etc.) */
  filters?: ReactNode;
  /** Placeholder del buscador */
  searchPlaceholder?: string;
  /** Callback de búsqueda (debounced 300ms) */
  onSearch?: (value: string) => void;
  /** Acciones a la derecha (botones) */
  actions?: ToolbarAction[];
  /** Contenido libre adicional (slots) */
  children?: ReactNode;
  /** Valor inicial del buscador */
  defaultSearch?: string;
  /** Deshabilitar buscador */
  disableSearch?: boolean;
  /** Clase externa para estilos */
  className?: string;
};

export const PageToolbar: React.FC<PageToolbarProps> = ({
  filters,
  searchPlaceholder = "Buscar…",
  onSearch,
  actions = [],
  children,
  defaultSearch = "",
  disableSearch = false,
  className,
}) => {
  const [value, setValue] = useState<string>(defaultSearch);

  useEffect(() => {
    setValue(defaultSearch);
  }, [defaultSearch]);

  // debounce simple
  useEffect(() => {
    if (!onSearch) return;
    const h = setTimeout(() => onSearch(value), 300);
    return () => clearTimeout(h);
  }, [value, onSearch]);

  const handleChange = useCallback<React.ChangeEventHandler<HTMLInputElement>>((e) => {
    setValue(e.target.value);
  }, []);

  const renderedActions = useMemo(() => {
    if (!actions?.length) return null;
    return (
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {actions.map((a) => (
          <button
            key={a.id}
            type="button"
            onClick={a.onClick}
            disabled={!!a.disabled}
            title={a.title || a.label}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              background: a.disabled ? "#3a3a3a" : "#2563eb",
              color: "#fff",
              border: "none",
              cursor: a.disabled ? "not-allowed" : "pointer",
            }}
          >
            {a.label}
          </button>
        ))}
      </div>
    );
  }, [actions]);

  return (
    <div
      className={className}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        padding: 12,
        borderRadius: 12,
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <input
          aria-label="Buscar"
          type="search"
          placeholder={searchPlaceholder}
          value={value}
          onChange={handleChange}
          disabled={disableSearch}
          style={{
            minWidth: 220,
            flex: "1 1 260px",
            padding: "10px 12px",
            borderRadius: 10,
            border: "1px solid rgba(255,255,255,0.12)",
            background: "rgba(0,0,0,0.25)",
            color: "#e5e7eb",
            outline: "none",
          }}
        />
        <div style={{ flex: "1 1 auto" }}>{filters}</div>
        {renderedActions}
      </div>
      {children ? <div>{children}</div> : null}
    </div>
  );
};

export default PageToolbar;
