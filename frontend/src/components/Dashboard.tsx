import DashboardLayout from "./dashboard/DashboardLayout";
import { DashboardProvider } from "./dashboard/DashboardContext";

type Props = {
  token: string;
};

function Dashboard({ token }: Props) {
  return (
    <DashboardProvider token={token}>
      <DashboardLayout />
    </DashboardProvider>
  );
}

export default Dashboard;
