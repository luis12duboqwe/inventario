import { useId, useMemo, useState, type FormEvent, type ReactNode } from "react";

import Button from "../../shared/components/ui/Button";
import type { PageHeaderAction } from "./PageHeader";

type PageToolbarProps = {
  actions?: PageHeaderAction[];
  onSearch?: (value: string) => void;
  searchPlaceholder?: string;
  filters?: ReactNode;
  children?: ReactNode;
};

function PageToolbarSM({
  actions,
  onSearch,
  searchPlaceholder = "Buscar…",
  filters,
  children,
}: PageToolbarProps) {
  const [searchValue, setSearchValue] = useState("");
  const searchId = useId();

  const toolbarActions = useMemo(() => actions ?? [], [actions]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!onSearch) {
      return;
    }
    onSearch(searchValue.trim());
  };

  return (
    <section className="page-toolbar-sm">
      <div className="page-toolbar-sm__row">
        {onSearch ? (
          <form className="page-toolbar-sm__search" onSubmit={handleSubmit} role="search">
            <label className="sr-only" htmlFor={searchId}>
              Buscar
            </label>
            <input
              id={searchId}
              type="search"
              placeholder={searchPlaceholder}
              value={searchValue}
              onChange={(event) => setSearchValue(event.target.value)}
            />
            <Button type="submit" variant="secondary" size="sm">
              Buscar
            </Button>
          </form>
        ) : null}

        {toolbarActions.length > 0 ? (
          <div className="page-toolbar-sm__actions">
            {toolbarActions.map((action) => (
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

      {filters ? <div className="page-toolbar-sm__filters">{filters}</div> : null}
      {children ? <div className="page-toolbar-sm__extra">{children}</div> : null}
    </section>
  );
}

export type { PageToolbarProps };
const PageToolbar = PageToolbarSM;

export { PageToolbarSM, PageToolbar };
export default PageToolbar;
