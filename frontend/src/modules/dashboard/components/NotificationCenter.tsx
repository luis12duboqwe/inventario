import { type SyntheticEvent, useEffect, useId, useState } from "react";

type NotificationVariant = "success" | "info" | "warning" | "error";

export type NotificationCenterItem = {
  id: string;
  title: string;
  description: string;
  variant: NotificationVariant;
};

type NotificationCenterProps = {
  summary: string;
  items: NotificationCenterItem[];
  roleVariant: "admin" | "manager" | "operator" | "guest";
  open?: boolean;
  onToggle?: (open: boolean) => void;
};

function NotificationCenter({
  summary,
  items,
  roleVariant,
  open = false,
  onToggle,
}: NotificationCenterProps) {
  const [isOpen, setIsOpen] = useState(open);
  const summaryId = useId();
  const regionId = useId();
  const hasItems = items.length > 0;

  useEffect(() => {
    setIsOpen(open);
  }, [open]);

  const handleToggle = (event: SyntheticEvent<HTMLDetailsElement>) => {
    const details = event.currentTarget;
    setIsOpen(details.open);
    onToggle?.(details.open);
  };

  return (
    <details
      className={`notification-center notification-center--${roleVariant}`}
      open={isOpen}
      onToggle={handleToggle}
      aria-labelledby={summaryId}
    >
      <summary
        id={summaryId}
        aria-live="polite"
        aria-controls={regionId}
        aria-expanded={isOpen}
      >
        <span className="notification-center__icon" aria-hidden="true">
          🔔
        </span>
        <span className="notification-center__summary-text">{summary}</span>
      </summary>
      <div
        id={regionId}
        className="notification-center__panel"
        role="region"
        aria-live="polite"
        aria-label="Detalle de notificaciones"
      >
        {hasItems ? (
          <ul className="notification-center__list">
            {items.map((item) => (
              <li
                key={item.id}
                className={`notification-center__item notification-center__item--${item.variant}`}
              >
                <span className="notification-center__item-title">{item.title}</span>
                <p className="notification-center__item-description">{item.description}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="notification-center__empty">No hay notificaciones activas.</p>
        )}
      </div>
    </details>
  );
}

export default NotificationCenter;
