import UserManagement from "../components/UserManagement";
import { useUsersModule } from "../hooks/useUsersModule";

function UsersPage() {
  const { token } = useUsersModule();

  return (
    <div className="section-grid">
      <UserManagement token={token} />
    </div>
  );
}

export default UsersPage;
