import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";

type TextFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "size"> & {
  label: string;
  helperText?: string;
  error?: string;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
  hideLabel?: boolean;
};

const TextField = forwardRef<HTMLInputElement, TextFieldProps>(
  (
    { id, label, helperText, error, leadingIcon, trailingIcon, className, hideLabel = false, ...rest },
    ref,
  ) => {
    const generatedId = useId();
    const fieldId = id ?? generatedId;
    const descriptionId = helperText ? `${fieldId}-helper` : undefined;
    const errorId = error ? `${fieldId}-error` : undefined;

    const classes = ["ui-field", error ? "ui-field--error" : "", className ?? ""].filter(Boolean).join(" ");
    const labelClassName = ["ui-field__label", hideLabel ? "sr-only" : ""].filter(Boolean).join(" ");

    return (
      <div className={classes}>
        <label className={labelClassName} htmlFor={fieldId}>
          {label}
        </label>
        <div className="ui-field__control">
          {leadingIcon ? <span className="ui-field__icon" aria-hidden="true">{leadingIcon}</span> : null}
          <input
            ref={ref}
            id={fieldId}
            className="ui-field__input"
            aria-describedby={[descriptionId, errorId].filter(Boolean).join(" ") || undefined}
            aria-invalid={error ? true : undefined}
            {...rest}
          />
          {trailingIcon ? <span className="ui-field__icon ui-field__icon--trailing" aria-hidden="true">{trailingIcon}</span> : null}
        </div>
        {helperText ? (
          <p id={descriptionId} className="ui-field__helper">
            {helperText}
          </p>
        ) : null}
        {error ? (
          <p id={errorId} className="ui-field__error">
            {error}
          </p>
        ) : null}
      </div>
    );
  },
);

TextField.displayName = "TextField";

export type { TextFieldProps };
export default TextField;
