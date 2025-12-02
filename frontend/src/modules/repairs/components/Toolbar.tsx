import type { ReactNode } from "react";

import type { PageHeaderAction } from "../../../components/layout/PageHeader";
import PageToolbar, { type ToolbarAction } from "../../../components/layout/PageToolbar";

type ToolbarProps = {
  actions: PageHeaderAction[];
  children: ReactNode;
};

function Toolbar({ actions, children }: ToolbarProps) {
  const mappedActions: ToolbarAction[] = actions.map((action) => {
    const base: ToolbarAction = {
      id: action.id ?? action.label,
      label: action.label,
      title: action.label,
    };

    if (typeof action.disabled === "boolean") {
      base.disabled = action.disabled;
    }

    if (action.onClick) {
      base.onClick = action.onClick;
    }

    return base;
  });

  return <PageToolbar actions={mappedActions} filters={children} disableSearch />;
}

export type { ToolbarProps };
export default Toolbar;
