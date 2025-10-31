export const colors = {
  backgroundPrimary: "#0d1117",
  backgroundSecondary: "#111827",
  surfaceRaised: "#162132",
  surfaceMuted: "#1d2a3f",
  surfaceOverlay: "rgba(9, 13, 23, 0.86)",
  surfaceTooltip: "rgba(15, 23, 42, 0.94)",
  borderSubtle: "#1f2b3d",
  borderStrong: "#23334a",
  accentBorder: "rgba(56, 189, 248, 0.35)",
  accent: "#38bdf8",
  accentSoft: "rgba(56, 189, 248, 0.18)",
  accentBright: "#22d3ee",
  accentDeep: "#0ea5e9",
  accentStrong: "#0f9bce",
  success: "#22c55e",
  successBright: "#4ade80",
  successGlow: "#5ff59c",
  warning: "#fbbf24",
  warningHighlight: "#facc15",
  warningStrong: "#f97316",
  danger: "#ef4444",
  dangerBright: "#f87171",
  dangerHighlight: "#fca5a5",
  dangerSoftContrast: "#ff9b94",
  dangerSoftStrong: "#ff8f89",
  info: "#38bdf8",
  infoHighlight: "#e0f2fe",
  textPrimary: "#f8fafc",
  textSecondary: "#cbd5f5",
  textMuted: "#94a3b8",
  textOnAccent: "#03121f",
  neutralSoft: "#e2e8f0",
  neutralSoftTint: "rgba(148, 163, 184, 0.18)",
  surfaceInput: "rgba(18, 27, 44, 0.88)",
  surfaceInteractive: "rgba(56, 189, 248, 0.12)",
  accentFocusBorder: "rgba(56, 189, 248, 0.55)",
  accentFocusRing: "rgba(56, 189, 248, 0.18)",
  accentSoftStrong: "rgba(56, 189, 248, 0.24)",
  successSoft: "rgba(34, 197, 94, 0.16)",
  successSurfaceStrong: "rgba(34, 197, 94, 0.22)",
  warningSoft: "rgba(251, 191, 36, 0.18)",
  dangerSoft: "rgba(239, 68, 68, 0.18)",
  dangerSurfaceStrong: "rgba(239, 68, 68, 0.24)",
  dangerSurfaceTint: "rgba(239, 68, 68, 0.2)",
  dangerBorderStrong: "rgba(239, 68, 68, 0.45)",
  dangerFocusBorder: "rgba(239, 68, 68, 0.6)",
  dangerFocusRing: "rgba(239, 68, 68, 0.18)",
  dangerOutlineBorder: "rgba(239, 68, 68, 0.65)",
  dangerOutlineRing: "rgba(239, 68, 68, 0.25)",
  infoSoft: "rgba(56, 189, 248, 0.16)",
  infoSurfaceStrong: "rgba(14, 165, 233, 0.2)",
  infoBorderStrong: "rgba(14, 165, 233, 0.55)",
  focus: "#38bdf8",
  overlay: "rgba(9, 13, 23, 0.72)",
  chartIndigo: "#1d4ed8",
  chartSky: "#0ea5e9",
  chartCyan: "#06b6d4",
  chartTeal: "#0d9488",
  chartMint: "#6ee7b7",
  chartAqua: "#5eead4",
  chartLavender: "#c4b5fd",
  chartPurple: "#6366f1",
  chartAmber: "#f59e0b",
  chartOrange: "#f97316",
  warningSoftText: "#fef3c7",
  dangerSoftText: "#fecaca",
};

export const spacing = {
  xs: "0.25rem",
  sm: "0.5rem",
  md: "0.75rem",
  lg: "1rem",
  xl: "1.5rem",
  xxl: "2rem",
};

export const radii = {
  sm: "8px",
  md: "12px",
  lg: "18px",
  pill: "999px",
};

export const typography = {
  fontFamily: '"Poppins", "Inter", "Segoe UI", system-ui, -apple-system, sans-serif',
  fontSizeBase: "16px",
  fontWeightNormal: 400,
  fontWeightSemibold: 600,
  fontWeightBold: 700,
  lineHeightBase: 1.5,
};

export const shadows = {
  sm: "0 8px 24px rgba(15, 23, 42, 0.25)",
  md: "0 16px 45px rgba(14, 165, 233, 0.15)",
  lg: "0 28px 68px rgba(14, 165, 233, 0.22)",
};

export const transitions = {
  base: "all 0.25s ease",
};

export type ColorToken = keyof typeof colors;
export type SpacingToken = keyof typeof spacing;
export type RadiusToken = keyof typeof radii;
export type ShadowToken = keyof typeof shadows;

const toCssVariableName = (prefix: string, token: string) =>
  `--${prefix}-${token.replace(/([A-Z])/g, "-$1").toLowerCase()}`;

const colorVariableNames = Object.fromEntries(
  (Object.keys(colors) as ColorToken[]).map((token) => [token, toCssVariableName("color", token)]),
) as Record<ColorToken, `--color-${string}`>;

const spacingVariableNames: Record<SpacingToken, `--space-${1 | 2 | 3 | 4 | 5 | 6}`> = {
  xs: "--space-1",
  sm: "--space-2",
  md: "--space-3",
  lg: "--space-4",
  xl: "--space-5",
  xxl: "--space-6",
};

const radiusVariableNames: Record<RadiusToken, `--radius-${"sm" | "md" | "lg" | "pill"}`> = {
  sm: "--radius-sm",
  md: "--radius-md",
  lg: "--radius-lg",
  pill: "--radius-pill",
};

const shadowVariableNames: Record<ShadowToken, `--shadow-${"sm" | "md" | "lg"}`> = {
  sm: "--shadow-sm",
  md: "--shadow-md",
  lg: "--shadow-lg",
};

export const colorVariables = colorVariableNames;
export const spacingVariables = spacingVariableNames;
export const radiusVariables = radiusVariableNames;
export const shadowVariables = shadowVariableNames;

export const colorVar = (token: ColorToken) => `var(${colorVariableNames[token]})`;
export const spacingVar = (token: SpacingToken) => `var(${spacingVariableNames[token]})`;
export const radiusVar = (token: RadiusToken) => `var(${radiusVariableNames[token]})`;
export const shadowVar = (token: ShadowToken) => `var(${shadowVariableNames[token]})`;
