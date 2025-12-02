import {
  forwardRef,
  useId,
  type InputHTMLAttributes,
  type TextareaHTMLAttributes,
  type ReactNode,
} from "react";

type BaseProps = {
  label: string;
  helperText?: string;
  error?: string;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
  hideLabel?: boolean;
};

type InputProps = BaseProps &
  Omit<InputHTMLAttributes<HTMLInputElement>, "size"> & {
    multiline?: false;
    rows?: never;
  };

type TextAreaProps = BaseProps &
  Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "size"> & {
    multiline: true;
    rows?: number;
  };

type TextFieldProps = InputProps | TextAreaProps;

const TextField = forwardRef<HTMLInputElement | HTMLTextAreaElement, TextFieldProps>(
  (props, ref) => {
    const {
      id,
      label,
      helperText,
      error,
      leadingIcon,
      trailingIcon,
      className,
      hideLabel = false,
      multiline = false,
      ...rest
    } = props;

    const generatedId = useId();
    const fieldId = id ?? generatedId;
    const descriptionId = helperText ? `${fieldId}-helper` : undefined;
    const errorId = error ? `${fieldId}-error` : undefined;

    const classes = ["ui-field", error ? "ui-field--error" : "", className ?? ""]
      .filter(Boolean)
      .join(" ");
    const labelClassName = ["ui-field__label", hideLabel ? "sr-only" : ""]
      .filter(Boolean)
      .join(" ");

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
          {multiline ? (
            <textarea
              ref={ref as React.ForwardedRef<HTMLTextAreaElement>}
              id={fieldId}
              className="ui-field__input ui-field__textarea"
              aria-describedby={[descriptionId, errorId].filter(Boolean).join(" ") || undefined}
              aria-invalid={error ? true : undefined}
              {...(rest as TextareaHTMLAttributes<HTMLTextAreaElement>)}
            />
          ) : (
            <input
              ref={ref as React.ForwardedRef<HTMLInputElement>}
              id={fieldId}
              className="ui-field__input"
              aria-describedby={[descriptionId, errorId].filter(Boolean).join(" ") || undefined}
              aria-invalid={error ? true : undefined}
              {...(rest as InputHTMLAttributes<HTMLInputElement>)}
            />
          )}
          {trailingIcon ? (
            <span className="ui-field__icon ui-field__icon--trailing" aria-hidden="true">
              {trailingIcon}
            </span>
          ) : null}
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
