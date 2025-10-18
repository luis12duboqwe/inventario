import type { ReactNode } from "react";

type PageHeaderProps = {
  title: string;
  description?: string;
  actions?: ReactNode;
};

function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <header className="page-header" role="banner">
      <div className="page-header__titles">
        <h1>{title}</h1>
        {description ? <p className="page-header__description">{description}</p> : null}
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}

export type { PageHeaderProps };
export default PageHeader;
