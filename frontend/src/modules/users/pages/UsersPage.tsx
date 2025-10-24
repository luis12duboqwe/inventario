import { UserCog } from "lucide-react";

import UserManagement from "../components/UserManagement";
import ModuleHeader from "../../../shared/components/ModuleHeader";
import { useUsersModule } from "../hooks/useUsersModule";

function UsersPage() {
  const { token } = useUsersModule();

  return (
    <div className="module-content">
      <ModuleHeader
        icon={<UserCog aria-hidden="true" />}
        title="Usuarios"
        subtitle="Gestiona roles, activaciones y motivos corporativos por cuenta"
        status="ok"
        statusLabel="Administración disponible"
      />
      <div className="section-scroll">
        <div className="section-grid">
          <UserManagement token={token} />
        </div>
      </div>
    </div>
  );
}

export default UsersPage;
