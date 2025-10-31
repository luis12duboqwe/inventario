import type { ReactNode } from "react";

type PurchasesToolbarProps = {
  error?: string | null;
  message?: string | null;
  extraContent?: ReactNode;
};

const PurchasesToolbar = ({ error, message, extraContent }: PurchasesToolbarProps) => {
  return (
    <>
      {error ? <div className="alert error">{error}</div> : null}
      {message ? <div className="alert success">{message}</div> : null}
      {extraContent}
    </>
  );
};

export default PurchasesToolbar;
