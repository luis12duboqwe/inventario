import { type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../../auth/useAuth";
import { Loader } from "@components/ui/Loader";

// [PACK28-guards]
type RequireAuthProps = {
  children: ReactNode;
};

// [PACK28-guards]
function RequireAuth({ children }: RequireAuthProps) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <Loader message="Verificando sesión…" variant="overlay" />;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <>{children}</>;
}

export default RequireAuth;
