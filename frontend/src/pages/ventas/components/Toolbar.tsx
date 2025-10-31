import type { ReactNode } from "react";

type Props = {
  title: string;
  subtitle: string;
  message: string | null;
  error: string | null;
  children: ReactNode;
};

function Toolbar({ title, subtitle, message, error, children }: Props) {
  return (
    <section className="card">
      <h2>{title}</h2>
      <p className="card-subtitle">{subtitle}</p>
      {message ? <div className="alert success">{message}</div> : null}
      {error ? <div className="alert error">{error}</div> : null}
      {children}
    </section>
  );
}

export default Toolbar;
