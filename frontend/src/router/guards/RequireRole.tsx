import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "../../auth/useAuth";
import { type Role } from "../../auth/roles";
import { useAuthz } from "../../auth/useAuthz";
import Loader from "../../shared/components/Loader";

// [PACK28-guards]
type RequireRoleProps = {
  roles: Role | Role[];
  children: ReactNode;
  fallback?: ReactNode;
};

// [PACK28-guards]
function RequireRole({ roles, children, fallback }: RequireRoleProps) {
  const { isLoading } = useAuth();
  const { hasRole } = useAuthz();

  if (isLoading) {
    return <Loader message="Verificando permisos…" variant="overlay" />;
  }

  if (!hasRole(roles)) {
    if (fallback) {
      return <>{fallback}</>;
    }
    return <Navigate to="/dashboard/inventory" replace />;
  }

  return <>{children}</>;
}

export default RequireRole;
