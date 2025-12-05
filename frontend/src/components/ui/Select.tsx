import { forwardRef, useId, type SelectHTMLAttributes, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  helperText?: string;
  error?: string;
  leadingIcon?: ReactNode;
  hideLabel?: boolean;
  options?: Array<{ value: string | number; label: string }>;
};

const Select = forwardRef<HTMLSelectElement, SelectProps>((props, ref) => {
  const {
    id,
    label,
    helperText,
    error,
    leadingIcon,
    className,
    hideLabel = false,
    children,
    options,
    ...rest
  } = props;

  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const descriptionId = helperText ? `${fieldId}-helper` : undefined;
  const errorId = error ? `${fieldId}-error` : undefined;

  const classes = ["ui-field", error ? "ui-field--error" : "", className ?? ""]
    .filter(Boolean)
    .join(" ");
  const labelClassName = ["ui-field__label", hideLabel ? "sr-only" : ""].filter(Boolean).join(" ");

  return (
    <div className={classes}>
      <label className={labelClassName} htmlFor={fieldId}>
        {label}
      </label>
      <div className="ui-field__control">
        {leadingIcon ? (
          <span className="ui-field__icon" aria-hidden="true">
            {leadingIcon}
          </span>
        ) : null}
        <select
          ref={ref}
          id={fieldId}
          className="ui-field__input ui-field__select"
          aria-describedby={[descriptionId, errorId].filter(Boolean).join(" ") || undefined}
          aria-invalid={error ? true : undefined}
          {...rest}
        >
          {options
            ? options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))
            : children}
        </select>
        <span
          className="ui-field__icon ui-field__icon--trailing pointer-events-none"
          aria-hidden="true"
        >
          <ChevronDown size={16} />
        </span>
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
});

Select.displayName = "Select";

export default Select;
