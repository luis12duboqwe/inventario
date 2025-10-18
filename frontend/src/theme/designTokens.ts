export const colors = {
  backgroundPrimary: "#0d1117",
  backgroundSecondary: "#111827",
  surfaceRaised: "#162132",
  surfaceMuted: "#1d2a3f",
  borderSubtle: "#1f2b3d",
  borderStrong: "#23334a",
  accent: "#38bdf8",
  accentSoft: "rgba(56, 189, 248, 0.18)",
  accentBright: "#22d3ee",
  accentDeep: "#0ea5e9",
  accentStrong: "#0f9bce",
  success: "#22c55e",
  warning: "#fbbf24",
  danger: "#ef4444",
  info: "#38bdf8",
  textPrimary: "#f8fafc",
  textSecondary: "#cbd5f5",
  textMuted: "#94a3b8",
  textOnAccent: "#03121f",
  surfaceInput: "rgba(18, 27, 44, 0.88)",
  surfaceInteractive: "rgba(56, 189, 248, 0.12)",
  successSoft: "rgba(34, 197, 94, 0.16)",
  warningSoft: "rgba(251, 191, 36, 0.18)",
  dangerSoft: "rgba(239, 68, 68, 0.18)",
  infoSoft: "rgba(56, 189, 248, 0.16)",
  focus: "#38bdf8",
  overlay: "rgba(9, 13, 23, 0.72)",
  chartIndigo: "#1d4ed8",
  chartSky: "#0ea5e9",
  chartCyan: "#06b6d4",
  chartTeal: "#0d9488",
  chartPurple: "#6366f1",
  chartAmber: "#f59e0b",
  chartOrange: "#f97316",
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
