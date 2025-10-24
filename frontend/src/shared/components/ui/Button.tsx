import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "link";
type ButtonSize = "sm" | "md" | "lg";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
};

function buildClassName(variant: ButtonVariant, size: ButtonSize, className?: string) {
  const classes = ["ui-button", `ui-button--${variant}`, `ui-button--${size}`];
  if (className) {
    classes.push(className);
  }
  return classes.join(" ");
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", leadingIcon, trailingIcon, className, children, ...rest }, ref) => {
    return (
      <button ref={ref} className={buildClassName(variant, size, className)} {...rest}>
        {leadingIcon ? <span className="ui-button__icon" aria-hidden="true">{leadingIcon}</span> : null}
        <span className="ui-button__label">{children}</span>
        {trailingIcon ? <span className="ui-button__icon" aria-hidden="true">{trailingIcon}</span> : null}
      </button>
    );
  },
);

Button.displayName = "Button";

export type { ButtonProps, ButtonVariant, ButtonSize };
export default Button;
