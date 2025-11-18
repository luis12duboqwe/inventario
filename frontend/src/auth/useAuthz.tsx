// [PACK26-AUTHZ-HOOK-START]
import { createContext, useContext, useMemo, type ReactElement, type ReactNode } from "react";
import { ROLE_MATRIX, type Perm, type Role } from "./roles";

export type CurrentUser = {
  id: string;
  name: string;
  role: Role;
};

const AuthzCtx = createContext<{ user: CurrentUser | null }>({ user: null });

export function AuthzProvider({ user, children }: { user: CurrentUser | null; children: ReactNode }) {
  return <AuthzCtx.Provider value={{ user }}>{children}</AuthzCtx.Provider>;
}

export function useAuthz(){
  const { user } = useContext(AuthzCtx);
  const can = useMemo(() => {
    const perms = user ? ROLE_MATRIX[user.role] ?? [] : [];
    return (p: Perm) => perms.includes(p);
  }, [user]);
  const hasAny = useMemo(() => {
    const perms = user ? ROLE_MATRIX[user.role] ?? [] : [];
    return (list: Perm[]) => list.some((p)=>perms.includes(p));
  }, [user]);
  // [PACK28-authz]
  const hasRole = useMemo(() => {
    return (roles: Role | Role[]) => {
      const currentRole = user?.role ?? null;
      const roleList = Array.isArray(roles) ? roles : [roles];
      return currentRole ? roleList.includes(currentRole) : false;
    };
  }, [user?.role]);
  return { user, can, hasAny, hasRole };
}

// Guardas de UI
export function RequirePerm({ perm, children, fallback=null }: { perm: Perm; children: ReactNode; fallback?: ReactNode }) {
  const { can } = useAuthz();
  return can(perm) ? <>{children}</> : <>{fallback}</>;
}
export function DisableIfNoPerm({ perm, children }: { perm: Perm; children: ReactElement }) {
  const { can } = useAuthz();
  const allowed = can(perm);
  return (allowed ? children : <span aria-disabled="true" style={{opacity:.5, pointerEvents:"none"}}>{children}</span>);
}

export { PERMS } from "./roles";
export type { Role } from "./roles";
// [PACK26-AUTHZ-HOOK-END]
