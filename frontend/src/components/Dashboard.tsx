import { DashboardProvider } from "../modules/dashboard/context/DashboardContext";
import DashboardRoutes from "../modules/dashboard/routes";

type Props = {
  token: string;
};

function Dashboard({ token }: Props) {
  return (
    <DashboardProvider token={token}>
      <DashboardRoutes />
    </DashboardProvider>
  );
}

export default Dashboard;
