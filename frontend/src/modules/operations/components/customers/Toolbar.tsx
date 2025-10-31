import type { ReactNode } from "react";

type CustomersToolbarProps = {
  error?: string | null;
  message?: string | null;
  extraContent?: ReactNode;
};

const CustomersToolbar = ({ error, message, extraContent }: CustomersToolbarProps) => (
  <>
    {error ? <div className="alert error">{error}</div> : null}
    {message ? <div className="alert success">{message}</div> : null}
    {extraContent}
  </>
);

export default CustomersToolbar;
