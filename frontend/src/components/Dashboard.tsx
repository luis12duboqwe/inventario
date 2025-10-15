import { DashboardProvider } from "../modules/dashboard/context/DashboardContext";
import DashboardRoutes from "../modules/dashboard/routes";

type Props = {
  token: string;
  theme: "dark" | "light";
  onToggleTheme: () => void;
  onLogout: () => void;
};

function Dashboard({ token, theme, onToggleTheme, onLogout }: Props) {
  return (
    <DashboardProvider token={token}>
      <DashboardRoutes theme={theme} onToggleTheme={onToggleTheme} onLogout={onLogout} />
    </DashboardProvider>
  );
}

export default Dashboard;
