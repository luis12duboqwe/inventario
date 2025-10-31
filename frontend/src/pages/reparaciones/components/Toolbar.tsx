import type { ReactNode } from "react";

import type { PageHeaderAction } from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";

type ToolbarProps = {
  actions: PageHeaderAction[];
  children: ReactNode;
};

function Toolbar({ actions, children }: ToolbarProps) {
  return (
    <PageToolbar actions={actions}>
      {children}
    </PageToolbar>
  );
}

export type { ToolbarProps };
export default Toolbar;
