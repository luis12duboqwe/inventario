import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useId, useMemo, type ReactNode } from "react";
import { createPortal } from "react-dom";

import Button from "./Button";

type ModalSize = "sm" | "md" | "lg" | "xl";

type ModalProps = {
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  size?: ModalSize;
  hideDismiss?: boolean;
  dismissLabel?: string;
  dismissDisabled?: boolean;
};

const sizeClassName: Record<ModalSize, string> = {
  sm: "ui-modal__dialog--sm",
  md: "ui-modal__dialog--md",
  lg: "ui-modal__dialog--lg",
  xl: "ui-modal__dialog--xl",
};

function Modal({
  open,
  title,
  description,
  onClose,
  children,
  footer,
  size = "md",
  hideDismiss = false,
  dismissLabel = "Cerrar",
  dismissDisabled = false,
}: ModalProps) {
  const titleId = useId();
  const descriptionId = useMemo(() => (description ? `${titleId}-description` : undefined), [description, titleId]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (typeof document === "undefined") {
    return null;
  }

  return createPortal(
    <AnimatePresence>
      {open ? (
        <div className="ui-modal" role="presentation">
          <motion.button
            type="button"
            className="ui-modal__backdrop"
            aria-label="Cerrar ventana"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={descriptionId}
            className={`ui-modal__dialog ${sizeClassName[size]}`}
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
          >
            <header className="ui-modal__header">
              <div>
                <h2 id={titleId}>{title}</h2>
                {description ? (
                  <p id={descriptionId} className="ui-modal__description">
                    {description}
                  </p>
                ) : null}
              </div>
              {!hideDismiss ? (
                <Button type="button" variant="ghost" onClick={onClose} disabled={dismissDisabled}>
                  {dismissLabel}
                </Button>
              ) : null}
            </header>
            <div className="ui-modal__content">{children}</div>
            <footer className="ui-modal__footer">
              {footer ?? (
                <Button type="button" variant="ghost" onClick={onClose}>
                  {dismissLabel}
                </Button>
              )}
            </footer>
          </motion.div>
        </div>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}

export type { ModalProps, ModalSize };
export default Modal;
