import { Role } from "./types";
import { DashboardAuditAlerts } from "./audit";
import { request, requestCollection } from "./client";

export type UserAccount = {
  id: number;
  username: string;
  full_name?: string | null;
  telefono?: string | null;
  is_active: boolean;
  rol: string;
  estado: string;
  created_at: string;
  last_login_at?: string | null;
  locked_until?: string | null;
  failed_login_attempts?: number;
  roles: Role[];
  store_id?: number | null;
  store_name?: string | null;
};

export type UserQueryFilters = {
  search?: string;
  role?: string;
  status?: "all" | "active" | "inactive" | "locked";
  storeId?: number;
};

export type UserCreateInput = {
  username: string;
  password: string;
  full_name?: string | null;
  telefono?: string | null;
  roles: string[];
  store_id?: number | null;
};

export type UserUpdateInput = {
  full_name?: string | null;
  telefono?: string | null;
  password?: string | null;
  store_id?: number | null;
};

export type RoleModulePermission = {
  module: string;
  can_view: boolean;
  can_edit: boolean;
  can_delete: boolean;
};

export type RolePermissionMatrix = {
  role: string;
  permissions: RoleModulePermission[];
};

export type UserDashboardTotals = {
  total: number;
  active: number;
  inactive: number;
  locked: number;
};

export type UserDashboardActivity = {
  id: number;
  action: string;
  created_at: string;
  severity: "info" | "warning" | "critical";
  performed_by_id?: number | null;
  performed_by_name?: string | null;
  target_user_id?: number | null;
  target_username?: string | null;
  details?: Record<string, unknown> | null;
};

export type UserSessionSummary = {
  session_id: number;
  user_id: number;
  username: string;
  created_at: string;
  last_used_at?: string | null;
  expires_at?: string | null;
  status: "activa" | "revocada" | "expirada";
  revoke_reason?: string | null;
};


export type UserDashboardMetrics = {
  generated_at: string;
  totals: UserDashboardTotals;
  recent_activity: UserDashboardActivity[];
  active_sessions: UserSessionSummary[];
  audit_alerts: DashboardAuditAlerts;
};

export function getCurrentUser(token: string): Promise<UserAccount> {
  return request<UserAccount>("/auth/me", { method: "GET" }, token);
}

export function listUsers(
  token: string,
  filters: UserQueryFilters = {},
  options: { signal?: AbortSignal } = {},
): Promise<UserAccount[]> {
  const params = new URLSearchParams();
  if (filters.search) {
    params.set("search", filters.search);
  }
  if (filters.role) {
    params.set("role", filters.role);
  }
  if (filters.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  if (typeof filters.storeId === "number") {
    params.set("store_id", String(filters.storeId));
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const requestOptions: RequestInit = { method: "GET" };
  if (typeof options.signal !== "undefined") {
    requestOptions.signal = options.signal ?? null;
  }
  return requestCollection<UserAccount>(
    `/users${suffix}`,
    requestOptions,
    token,
  );
}

export function listRoles(token: string): Promise<Role[]> {
  return requestCollection<Role>("/users/roles", { method: "GET" }, token);
}

export function updateUserRoles(token: string, userId: number, roles: string[], reason: string): Promise<UserAccount> {
  return request<UserAccount>(
    `/users/${userId}/roles`,
    { method: "PUT", body: JSON.stringify({ roles }), headers: { "X-Reason": reason } },
    token
  );
}

export function updateUserStatus(token: string, userId: number, isActive: boolean, reason: string): Promise<UserAccount> {
  return request<UserAccount>(
    `/users/${userId}`,
    { method: "PATCH", body: JSON.stringify({ is_active: isActive }), headers: { "X-Reason": reason } },
    token
  );
}

export function createUser(
  token: string,
  payload: UserCreateInput,
  reason?: string,
): Promise<UserAccount> {
  const headers: Record<string, string> = {};
  if (reason) {
    headers["X-Reason"] = reason;
  }
  return request<UserAccount>("/users", { method: "POST", body: JSON.stringify(payload), headers }, token);
}

export function updateUser(
  token: string,
  userId: number,
  payload: UserUpdateInput,
  reason: string,
): Promise<UserAccount> {
  return request<UserAccount>(
    `/users/${userId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export function listRolePermissions(token: string, role?: string): Promise<RolePermissionMatrix[]> {
  const params = new URLSearchParams();
  if (role) {
    params.set("role", role);
  }
  const suffix = params.toString() ? `?${params}` : "";
  return requestCollection<RolePermissionMatrix>(
    `/users/permissions${suffix}`,
    { method: "GET" },
    token,
  );
}

export function updateRolePermissions(
  token: string,
  role: string,
  permissions: RoleModulePermission[],
  reason: string,
): Promise<RolePermissionMatrix> {
  return request<RolePermissionMatrix>(
    `/users/roles/${encodeURIComponent(role)}/permissions`,
    {
      method: "PUT",
      body: JSON.stringify({ permissions }),
      headers: { "X-Reason": reason },
    },
    token,
  );
}

export function getUserDashboard(token: string): Promise<UserDashboardMetrics> {
  return request<UserDashboardMetrics>("/users/dashboard", { method: "GET" }, token);
}

export function exportUsers(
  token: string,
  format: "pdf" | "xlsx",
  filters: UserQueryFilters = {},
  reason: string,
): Promise<Blob> {
  const params = new URLSearchParams();
  params.set("format", format);
  if (filters.search) {
    params.set("search", filters.search);
  }
  if (filters.role) {
    params.set("role", filters.role);
  }
  if (filters.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  if (typeof filters.storeId === "number") {
    params.set("store_id", String(filters.storeId));
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request<Blob>(
    `/users/export${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}
export type { Role } from "./types";
