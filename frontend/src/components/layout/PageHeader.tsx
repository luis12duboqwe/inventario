import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { Search } from "lucide-react";

import Button, { type ButtonVariant } from "@components/ui/Button";

export type PageHeaderAction = {
  id?: string;
  label: string;
  onClick?: () => void;
  icon?: ReactNode;
  variant?: ButtonVariant;
  disabled?: boolean;
  type?: "button" | "submit";
};

export type PageHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: PageHeaderAction[];
  onSearch?: (value: string) => void;
  searchPlaceholder?: string;
  filters?: ReactNode;
  children?: ReactNode;
};

function PageHeaderSM({
  title,
  subtitle,
  actions,
  onSearch,
  searchPlaceholder = "Buscar…",
  filters,
  children,
}: PageHeaderProps) {
  const [searchValue, setSearchValue] = useState("");

  const headerActions = useMemo(() => actions ?? [], [actions]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!onSearch) {
      return;
    }
    onSearch(searchValue.trim());
  };

  return (
    <header className="page-header-sm">
      <div className="page-header-sm__head">
        <div className="page-header-sm__titles">
          <h1 className="page-header-sm__title">{title}</h1>
          {subtitle ? <p className="page-header-sm__subtitle">{subtitle}</p> : null}
        </div>
        {headerActions.length > 0 ? (
          <div className="page-header-sm__actions">
            {headerActions.map((action) => (
              <Button
                key={action.id ?? action.label}
                variant={action.variant ?? "primary"}
                size="sm"
                type={action.type ?? "button"}
                onClick={action.onClick}
                disabled={action.disabled}
                leadingIcon={action.icon}
              >
                {action.label}
              </Button>
            ))}
          </div>
        ) : null}
      </div>

      {onSearch ? (
        <form className="page-header-sm__search" onSubmit={handleSubmit} role="search">
          <label className="page-header-sm__search-label">
            <span className="sr-only">Buscar</span>
            <span className="page-header-sm__search-icon" aria-hidden="true">
              <Search size={16} />
            </span>
            <input
              type="search"
              placeholder={searchPlaceholder}
              value={searchValue}
              onChange={(event) => setSearchValue(event.target.value)}
            />
          </label>
          <Button type="submit" variant="secondary" size="sm">
            Buscar
          </Button>
        </form>
      ) : null}

      {filters ? <div className="page-header-sm__filters">{filters}</div> : null}
      {children ? <div className="page-header-sm__extra">{children}</div> : null}
    </header>
  );
}

const PageHeader = PageHeaderSM;

export { PageHeaderSM, PageHeader };
export default PageHeader;
