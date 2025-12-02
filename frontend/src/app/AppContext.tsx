import { createContext, useContext } from "react";
import type { Credentials } from "@api/auth";
import type { ThemeMode } from "../router";

export type AppContextValue = {
  token: string | null;
  loading: boolean;
  error: string | null;
  theme: ThemeMode;
  themeLabel: string;
  onToggleTheme: () => void;
  onLogin: (credentials: Credentials) => Promise<void>;
  onLogout: () => void;
};

export const AppContext = createContext<AppContextValue | null>(null);

export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useAppContext must be used within an AppProvider");
  }
  return context;
}
