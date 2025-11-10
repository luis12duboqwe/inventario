const RTN_DIGIT_LENGTH = 14;

export const RTN_FORMAT_HINT = "####-####-######";
export const RTN_ERROR_MESSAGE = `Indica un RTN válido (${RTN_DIGIT_LENGTH} dígitos, formato ${RTN_FORMAT_HINT}).`;

const RTN_DIGIT_REGEX = /\d+/g;

const RTN_SANITIZE_REGEX = /[^0-9]/g;

export const normalizeRtn = (value: string | null | undefined): string | null => {
  const raw = value ?? "";
  const digits = raw.replace(RTN_SANITIZE_REGEX, "");
  if (digits.length !== RTN_DIGIT_LENGTH) {
    return null;
  }
  return `${digits.slice(0, 4)}-${digits.slice(4, 8)}-${digits.slice(8)}`;
};

export const isValidRtn = (value: string | null | undefined): boolean => normalizeRtn(value) !== null;

export const suggestRtnCompletion = (value: string | null | undefined): string => {
  const digits = (value ?? "").match(RTN_DIGIT_REGEX)?.join("") ?? "";
  const padded = digits.padEnd(RTN_DIGIT_LENGTH, "•").slice(0, RTN_DIGIT_LENGTH);
  return `${padded.slice(0, 4)}-${padded.slice(4, 8)}-${padded.slice(8)}`;
};
