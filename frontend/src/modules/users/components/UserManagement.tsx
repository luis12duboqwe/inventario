import { useCallback, useEffect, useMemo, useState } from "react";

import type {
  Role,
  RoleModulePermission,
  RolePermissionMatrix,
  UserAccount,
  UserDashboardMetrics,
  UserQueryFilters,
  UserCreateInput,
  UserUpdateInput,
} from "@api/users";
import type { Store } from "@api/stores";
import { listRoles } from "@api/users";
import { getStores } from "@api/stores";
import { FILTER_ALL_VALUE } from "../../../constants/filters";
import FiltersPanel from "./management/FiltersPanel";
import RoleModal from "./management/RoleModal";
import SidePanel from "./management/SidePanel";
import SummaryCards from "./management/SummaryCards";
import UsersTable from "./management/Table";
import Toolbar from "./management/Toolbar";
import type { UserFormState } from "./management/types";
import { useUsersModule } from "../hooks/useUsersModule";
import { usersService } from "../services/usersService";

type Props = {
  token: string;
};

type UserStatusFilter = typeof FILTER_ALL_VALUE | "active" | "inactive" | "locked";

const DEFAULT_FORM_STATE: UserFormState = {
  username: "",
  fullName: "",
  telefono: "",
  password: "",
  storeId: "none",
  roles: [],
};

function ensureReason(): string | null {
  const value = window.prompt("Describe el motivo corporativo (mínimo 5 caracteres)");
  if (!value) {
    return null;
  }
  return value.trim().length >= 5 ? value.trim() : null;
}

function UserManagement({ token }: Props) {
  const { pushToast, currentUser } = useUsersModule();
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [dashboard, setDashboard] = useState<UserDashboardMetrics | null>(null);
  const [permissionsMatrix, setPermissionsMatrix] = useState<RolePermissionMatrix[]>([]);
  const [permissionDraft, setPermissionDraft] = useState<Record<string, RoleModulePermission[]>>(
    {},
  );
  const [selectedRole, setSelectedRole] = useState<string>("OPERADOR");
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [formState, setFormState] = useState<UserFormState>(DEFAULT_FORM_STATE);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>(FILTER_ALL_VALUE);
  const [statusFilter, setStatusFilter] = useState<UserStatusFilter>(FILTER_ALL_VALUE);
  const [storeFilter, setStoreFilter] = useState<number | typeof FILTER_ALL_VALUE>(
    FILTER_ALL_VALUE,
  );
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingDashboard, setLoadingDashboard] = useState(false);
  const [loadingPermissions, setLoadingPermissions] = useState(false);
  const [savingPermissions, setSavingPermissions] = useState(false);
  const [savingUser, setSavingUser] = useState(false);
  const [exporting, setExporting] = useState<"pdf" | "xlsx" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);

  const debouncedSearch = useMemo(() => search.trim(), [search]);

  const filtersForQuery = useMemo<UserQueryFilters>(() => {
    const filters: UserQueryFilters = { status: statusFilter };
    if (debouncedSearch) {
      filters.search = debouncedSearch;
    }
    if (roleFilter !== FILTER_ALL_VALUE) {
      filters.role = roleFilter;
    }
    if (storeFilter !== FILTER_ALL_VALUE) {
      filters.storeId = storeFilter;
    }
    return filters;
  }, [debouncedSearch, roleFilter, statusFilter, storeFilter]);

  const selectedUser = useMemo(
    () => users.find((user) => user.id === selectedUserId) ?? null,
    [users, selectedUserId],
  );

  useEffect(() => {
    if (selectedUser) {
      setFormState({
        username: selectedUser.username,
        fullName: selectedUser.full_name ?? "",
        telefono: selectedUser.telefono ?? "",
        password: "",
        storeId: selectedUser.store_id ?? "none",
        roles: selectedUser.roles.map((role) => role.name),
      });
    } else {
      setFormState(DEFAULT_FORM_STATE);
    }
  }, [selectedUser]);

  const loadDashboard = useCallback(async () => {
    try {
      setLoadingDashboard(true);
      const data = await usersService.getUserDashboard(token);
      setDashboard(data);
    } catch (error_) {
      const message =
        error_ instanceof Error ? error_.message : "No fue posible cargar el panel de seguridad.";
      pushToast({ message, variant: "error" });
    } finally {
      setLoadingDashboard(false);
    }
  }, [token, pushToast]);

  const loadPermissions = useCallback(async () => {
    try {
      setLoadingPermissions(true);
      const data = await usersService.listRolePermissions(token);
      setPermissionsMatrix(data);
      if (data.length === 0) {
        setPermissionDraft({});
        setSelectedRole("");
        return;
      }
      const mapping: Record<string, RoleModulePermission[]> = {};
      data.forEach((item) => {
        mapping[item.role] = item.permissions.map((permission) => ({ ...permission }));
      });
      setPermissionDraft(mapping);
      setSelectedRole((current) => {
        if (current && data.some((item) => item.role === current)) {
          return current;
        }
        return data[0]!.role;
      });
    } catch (error_) {
      const message =
        error_ instanceof Error
          ? error_.message
          : "No fue posible cargar los permisos corporativos.";
      pushToast({ message, variant: "error" });
    } finally {
      setLoadingPermissions(false);
    }
  }, [token, pushToast]);

  useEffect(() => {
    let active = true;
    const initialize = async () => {
      try {
        const [rolesData, storesData] = await Promise.all([listRoles(token), getStores(token)]);
        if (!active) {
          return;
        }
        setRoles(rolesData);
        setStores(storesData);
      } catch (error_) {
        const message =
          error_ instanceof Error
            ? error_.message
            : "No fue posible cargar los catálogos de seguridad.";
        if (active) {
          pushToast({ message, variant: "error" });
        }
      }
    };
    void initialize();
    void loadDashboard();
    void loadPermissions();
    return () => {
      active = false;
    };
  }, [token, pushToast, loadDashboard, loadPermissions]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setLoadingUsers(true);
    usersService
      .listUsers(token, filtersForQuery, { signal: controller.signal })
      .then((data) => {
        if (!active) {
          return;
        }
        setUsers(data);
        setError(null);
      })
      .catch((error_) => {
        if (controller.signal.aborted || !active) {
          return;
        }
        const message =
          error_ instanceof Error ? error_.message : "No fue posible cargar la lista de usuarios.";
        setError(message);
        pushToast({ message, variant: "error" });
      })
      .finally(() => {
        if (active) {
          setLoadingUsers(false);
        }
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [token, filtersForQuery, pushToast]);

  const reloadUsers = useCallback(async () => {
    try {
      setLoadingUsers(true);
      const data = await usersService.listUsers(token, filtersForQuery);
      setUsers(data);
      setError(null);
    } catch (error_) {
      const message =
        error_ instanceof Error
          ? error_.message
          : "No fue posible actualizar la lista de usuarios.";
      pushToast({ message, variant: "error" });
    } finally {
      setLoadingUsers(false);
    }
  }, [token, filtersForQuery, pushToast]);

  const handleRoleToggle = async (user: UserAccount, roleName: string, checked: boolean) => {
    const reason = ensureReason();
    if (!reason) {
      pushToast({ message: "Operación cancelada: motivo inválido", variant: "info" });
      return;
    }
    const updatedRoles = checked
      ? Array.from(new Set([...user.roles.map((role) => role.name), roleName]))
      : user.roles.map((role) => role.name).filter((role) => role !== roleName);
    try {
      const updated = await usersService.updateUserRoles(token, user.id, updatedRoles, reason);
      setUsers((current) => current.map((item) => (item.id === user.id ? updated : item)));
      pushToast({ message: `Roles actualizados para ${user.username}`, variant: "success" });
      void loadDashboard();
    } catch (error_) {
      const message =
        error_ instanceof Error
          ? error_.message
          : "No fue posible actualizar los roles del usuario.";
      pushToast({ message, variant: "error" });
    }
  };

  const handleStatusToggle = async (user: UserAccount, isActive: boolean) => {
    const reason = ensureReason();
    if (!reason) {
      pushToast({ message: "Operación cancelada: motivo inválido", variant: "info" });
      return;
    }
    try {
      const updated = await usersService.updateUserStatus(token, user.id, isActive, reason);
      setUsers((current) => current.map((item) => (item.id === user.id ? updated : item)));
      pushToast({ message: `Estado actualizado para ${user.username}`, variant: "success" });
      void loadDashboard();
    } catch (error_) {
      const message =
        error_ instanceof Error
          ? error_.message
          : "No fue posible actualizar el estado del usuario.";
      pushToast({ message, variant: "error" });
    }
  };

  const handleFormSubmit = async () => {
    if (savingUser) {
      return;
    }
    if (selectedUser) {
      const updates: UserUpdateInput = {};
      const trimmedName = formState.fullName.trim();
      if (trimmedName !== (selectedUser.full_name ?? "")) {
        updates.full_name = trimmedName || null;
      }
      const trimmedPhone = formState.telefono.trim();
      if (trimmedPhone !== (selectedUser.telefono ?? "")) {
        updates.telefono = trimmedPhone || null;
      }
      if (formState.password.trim()) {
        updates.password = formState.password.trim();
      }
      const currentStore = selectedUser.store_id ?? null;
      const nextStore = formState.storeId === "none" ? null : formState.storeId;
      if (nextStore !== currentStore) {
        updates.store_id = nextStore;
      }
      if (Object.keys(updates).length === 0) {
        pushToast({ message: "No hay cambios por guardar.", variant: "info" });
        return;
      }
      const reason = ensureReason();
      if (!reason) {
        pushToast({ message: "Operación cancelada: motivo inválido", variant: "info" });
        return;
      }
      try {
        setSavingUser(true);
        const updated = await usersService.updateUser(token, selectedUser.id, updates, reason);
        setUsers((current) =>
          current.map((item) => (item.id === selectedUser.id ? updated : item)),
        );
        pushToast({
          message: `Usuario ${updated.username} actualizado correctamente`,
          variant: "success",
        });
        setSelectedUserId(updated.id);
        void loadDashboard();
      } catch (error_) {
        const message =
          error_ instanceof Error
            ? error_.message
            : "No fue posible actualizar la cuenta corporativa.";
        pushToast({ message, variant: "error" });
      } finally {
        setSavingUser(false);
        setFormState((current) => ({ ...current, password: "" }));
      }
      return;
    }

    const trimmedUsername = formState.username.trim();
    if (!trimmedUsername) {
      pushToast({ message: "El correo corporativo es obligatorio.", variant: "warning" });
      return;
    }
    if (formState.password.length < 8) {
      pushToast({ message: "La contraseña debe tener al menos 8 caracteres.", variant: "warning" });
      return;
    }
    if (formState.roles.length === 0) {
      pushToast({ message: "Selecciona al menos un rol corporativo.", variant: "warning" });
      return;
    }

    const payload: UserCreateInput = {
      username: trimmedUsername,
      password: formState.password,
      roles: formState.roles,
    };

    const trimmedFullName = formState.fullName.trim();
    if (trimmedFullName) {
      payload.full_name = trimmedFullName;
    }

    const trimmedPhone = formState.telefono.trim();
    if (trimmedPhone) {
      payload.telefono = trimmedPhone;
    }

    if (formState.storeId !== "none") {
      payload.store_id = formState.storeId;
    }

    try {
      setSavingUser(true);
      const created = await usersService.createUser(token, payload);
      pushToast({
        message: `Usuario ${created.username} creado correctamente`,
        variant: "success",
      });
      setFormState(DEFAULT_FORM_STATE);
      setSelectedUserId(created.id);
      await reloadUsers();
      void loadDashboard();
    } catch (error_) {
      const message =
        error_ instanceof Error ? error_.message : "No fue posible registrar al nuevo usuario.";
      pushToast({ message, variant: "error" });
    } finally {
      setSavingUser(false);
    }
  };

  const handleExport = async (format: "pdf" | "xlsx") => {
    const reason = ensureReason();
    if (!reason) {
      pushToast({ message: "Operación cancelada: motivo inválido", variant: "info" });
      return;
    }
    try {
      setExporting(format);
      const blob = await usersService.exportUsers(token, format, filtersForQuery, reason);
      const filename = `usuarios_softmobile.${format}`;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      pushToast({
        message: `Reporte ${format.toUpperCase()} generado correctamente`,
        variant: "success",
      });
    } catch (error_) {
      const message =
        error_ instanceof Error ? error_.message : "No fue posible exportar la lista de usuarios.";
      pushToast({ message, variant: "error" });
    } finally {
      setExporting(null);
    }
  };

  const baselinePermissions = useMemo(() => {
    return permissionsMatrix.find((item) => item.role === selectedRole)?.permissions ?? [];
  }, [permissionsMatrix, selectedRole]);

  const currentPermissions = useMemo(() => {
    return (
      permissionDraft[selectedRole] ?? baselinePermissions.map((permission) => ({ ...permission }))
    );
  }, [permissionDraft, selectedRole, baselinePermissions]);

  const sensitivePermissions = useMemo(() => {
    return currentPermissions.filter((permission) => permission.can_delete || permission.can_edit);
  }, [currentPermissions]);

  const hasPermissionChanges = useMemo(() => {
    if (baselinePermissions.length !== currentPermissions.length) {
      return true;
    }
    const baselineMap = new Map(
      baselinePermissions.map((permission) => [permission.module, permission] as const),
    );
    return currentPermissions.some((permission) => {
      const baseline = baselineMap.get(permission.module);
      if (!baseline) {
        return true;
      }
      return (
        baseline.can_view !== permission.can_view ||
        baseline.can_edit !== permission.can_edit ||
        baseline.can_delete !== permission.can_delete
      );
    });
  }, [baselinePermissions, currentPermissions]);

  const handlePermissionToggle = (module: string, field: keyof RoleModulePermission) => {
    setPermissionDraft((current) => {
      const permissions =
        current[selectedRole] ?? baselinePermissions.map((permission) => ({ ...permission }));
      const updated = permissions.map((permission) =>
        permission.module === module ? { ...permission, [field]: !permission[field] } : permission,
      );
      return { ...current, [selectedRole]: updated };
    });
  };

  const handleSensitiveToggle = (module: string) => {
    handlePermissionToggle(module, "can_delete");
  };

  const handlePermissionReset = () => {
    setPermissionDraft((current) => ({
      ...current,
      [selectedRole]: baselinePermissions.map((permission) => ({ ...permission })),
    }));
  };

  const handlePermissionSave = async () => {
    const reason = ensureReason();
    if (!reason) {
      pushToast({ message: "Operación cancelada: motivo inválido", variant: "info" });
      return;
    }
    try {
      setSavingPermissions(true);
      const updated = await usersService.updateRolePermissions(
        token,
        selectedRole,
        currentPermissions,
        reason,
      );
      setPermissionsMatrix((current) => {
        const filtered = current.filter((item) => item.role !== updated.role);
        return [...filtered, updated].sort((a, b) => a.role.localeCompare(b.role));
      });
      setPermissionDraft((current) => ({
        ...current,
        [updated.role]: updated.permissions.map((permission) => ({ ...permission })),
      }));
      pushToast({ message: `Permisos actualizados para ${updated.role}`, variant: "success" });
      setIsRoleModalOpen(false);
    } catch (error_) {
      const message =
        error_ instanceof Error
          ? error_.message
          : "No fue posible actualizar los permisos del rol.";
      pushToast({ message, variant: "error" });
    } finally {
      setSavingPermissions(false);
    }
  };

  const sortedRoles = useMemo(() => {
    return [...roles].sort((a, b) => a.name.localeCompare(b.name));
  }, [roles]);

  const roleNames = useMemo(() => {
    const uniqueNames = new Set(sortedRoles.map((role) => role.name));
    return Array.from(uniqueNames);
  }, [sortedRoles]);

  const sortedPermissionsMatrix = useMemo(() => {
    return [...permissionsMatrix].sort((a, b) => a.role.localeCompare(b.role));
  }, [permissionsMatrix]);

  return (
    <section className="card user-management">
      <Toolbar
        onExportPdf={() => handleExport("pdf")}
        onExportExcel={() => handleExport("xlsx")}
        disabled={exporting !== null}
        error={error}
      />
      <SummaryCards dashboard={dashboard} loading={loadingDashboard} onRefresh={loadDashboard} />
      <div className="user-management__content">
        <div className="user-management__main">
          <FiltersPanel
            search={search}
            onSearchChange={setSearch}
            roleFilter={roleFilter}
            onRoleFilterChange={setRoleFilter}
            statusFilter={statusFilter}
            onStatusFilterChange={(value) => setStatusFilter(value ?? FILTER_ALL_VALUE)}
            storeFilter={storeFilter}
            onStoreFilterChange={(value) => setStoreFilter(value)}
            roleOptions={roleNames}
            stores={stores}
          />
          <UsersTable
            users={users}
            roleNames={roleNames}
            selectedUserId={selectedUserId}
            onSelectUser={setSelectedUserId}
            onToggleStatus={handleStatusToggle}
            onToggleRole={handleRoleToggle}
            currentUserId={currentUser?.id ?? null}
            loading={loadingUsers}
          />
        </div>
        <div className="user-management__side">
          <SidePanel
            mode={selectedUser ? "edit" : "create"}
            formValues={formState}
            onFormChange={(patch) => setFormState((current) => ({ ...current, ...patch }))}
            onFormSubmit={handleFormSubmit}
            onFormReset={() => {
              setSelectedUserId(null);
              setFormState(DEFAULT_FORM_STATE);
            }}
            roles={sortedRoles}
            stores={stores}
            savingUser={savingUser}
            permissionsMatrix={sortedPermissionsMatrix}
            selectedRole={selectedRole}
            permissions={currentPermissions}
            onSelectRole={setSelectedRole}
            onTogglePermission={handlePermissionToggle}
            onResetPermissions={handlePermissionReset}
            onSavePermissions={handlePermissionSave}
            savingPermissions={savingPermissions}
            loadingPermissions={loadingPermissions}
            hasPermissionChanges={hasPermissionChanges}
            onOpenRoleModal={() => setIsRoleModalOpen(true)}
          />
          <section className="card card-section sensitive-permissions">
            <header className="permissions-panel__header">
              <div>
                <h3>Acciones sensibles por sucursal</h3>
                <p className="card-subtitle">
                  Activa o desactiva la eliminación por módulo; se limitará a la sucursal asignada
                  del usuario.
                </p>
              </div>
            </header>
            {sensitivePermissions.length === 0 ? (
              <p className="muted-text">No hay módulos marcados como sensibles para este rol.</p>
            ) : (
              <ul className="sensitive-permissions__list">
                {sensitivePermissions.map((permission) => (
                  <li key={permission.module} className="sensitive-permissions__item">
                    <div>
                      <p className="permissions-table__module">{permission.module}</p>
                      <small className="muted-text">
                        Requiere rol activo en la sucursal objetivo.
                      </small>
                    </div>
                    <label className="checkbox-control">
                      <input
                        type="checkbox"
                        checked={permission.can_delete}
                        onChange={() => handleSensitiveToggle(permission.module)}
                        aria-label={`Permitir eliminar en módulo ${permission.module}`}
                      />
                      <span />
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
      <RoleModal
        open={isRoleModalOpen}
        onClose={() => setIsRoleModalOpen(false)}
        roles={sortedPermissionsMatrix}
        selectedRole={selectedRole}
        permissions={currentPermissions}
        onSelectRole={setSelectedRole}
        onToggle={handlePermissionToggle}
        onReset={handlePermissionReset}
        onSave={handlePermissionSave}
        saving={savingPermissions}
        loading={loadingPermissions}
        hasChanges={hasPermissionChanges}
      />
    </section>
  );
}

export default UserManagement;
