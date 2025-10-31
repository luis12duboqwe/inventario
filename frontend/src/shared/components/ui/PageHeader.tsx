import type { ReactNode } from "react";

type PageHeaderStatusTone = "ok" | "warning" | "critical" | "info";

type PageHeaderStatus = {
  tone: PageHeaderStatusTone;
  label: string;
};

type PageHeaderProps = {
  title: string;
  description?: string;
  leadingIcon?: ReactNode;
  status?: PageHeaderStatus;
  actions?: ReactNode;
  meta?: ReactNode;
  className?: string;
};

function PageHeader({
  title,
  description,
  leadingIcon,
  status,
  actions,
  meta,
  className,
}: PageHeaderProps) {
  const headerClassName = ["page-header", className ?? ""].filter(Boolean).join(" ");

  return (
    <header className={headerClassName} role="banner">
      {leadingIcon ? (
        <div className="page-header__icon" aria-hidden="true">
          {leadingIcon}
        </div>
      ) : null}
      <div className="page-header__body">
        <div className="page-header__title-row">
          <h1>{title}</h1>
          {status ? (
            <span className={`page-header__status page-header__status--${status.tone}`} role="status">
              <span className="page-header__status-dot" aria-hidden="true" />
              <span className="page-header__status-label">{status.label}</span>
            </span>
          ) : null}
        </div>
        {description ? <p className="page-header__description">{description}</p> : null}
        {meta ? <div className="page-header__meta">{meta}</div> : null}
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}

export type { PageHeaderProps, PageHeaderStatus, PageHeaderStatusTone };
export default PageHeader;
