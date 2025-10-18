import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  FileSpreadsheet,
  FileText,
  RefreshCcw,
  ShieldAlert,
  Users as UsersIcon,
} from "lucide-react";

import type {
  Role,
  RoleModulePermission,
  RolePermissionMatrix,
  Store,
  UserAccount,
  UserDashboardMetrics,
} from "../../../api";
import { getStores, listRoles } from "../../../api";
import LoadingOverlay from "../../../components/LoadingOverlay";
import { useUsersModule } from "../hooks/useUsersModule";
import { usersService } from "../services/usersService";

import type { UserQueryFilters, UserCreateInput, UserUpdateInput } from "../../../api";

type Props = {
  token: string;
};

type FormState = {
  username: string;
  fullName: string;
  telefono: string;
  password: string;
  storeId: number | "none";
  roles: string[];
};

const DEFAULT_FORM_STATE: FormState = {
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

const formatDateTime = (value: string | null | undefined): string => {
  if (!value) {
    return "—";
  }
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return new Intl.DateTimeFormat("es-MX", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(date);
  } catch {
    return value;
  }
};

type UserDashboardPanelProps = {
  dashboard: UserDashboardMetrics | null;
  loading: boolean;
  onRefresh: () => void;
};

function UserDashboardPanel({ dashboard, loading, onRefresh }: UserDashboardPanelProps) {
  const totals = dashboard?.totals ?? { total: 0, active: 0, inactive: 0, locked: 0 };
  const recentActivity = dashboard?.recent_activity.slice(0, 5) ?? [];
  const recentSessions = dashboard?.active_sessions.slice(0, 5) ?? [];
  const alerts = dashboard?.audit_alerts;

  return (
    <section className="user-dashboard card-section">
      <header className="user-dashboard__header">
        <div>
          <h3>Panel de seguridad y accesos</h3>
          <p className="card-subtitle">Actividad reciente, sesiones activas y alertas corporativas</p>
        </div>
        <button type="button" className="button button-secondary" onClick={onRefresh} disabled={loading}>
          <RefreshCcw size={16} aria-hidden="true" />
          Actualizar
        </button>
      </header>
      <div className="user-dashboard__body">
        <div className="user-dashboard__totals">
          <div className="stat-card">
            <UsersIcon size={18} aria-hidden="true" />
            <div>
              <span className="stat-card__label">Usuarios totales</span>
              <strong className="stat-card__value">{totals.total}</strong>
            </div>
          </div>
          <div className="stat-card stat-card--success">
            <UsersIcon size={18} aria-hidden="true" />
            <div>
              <span className="stat-card__label">Activos</span>
              <strong className="stat-card__value">{totals.active}</strong>
            </div>
          </div>
          <div className="stat-card stat-card--warning">
            <UsersIcon size={18} aria-hidden="true" />
            <div>
              <span className="stat-card__label">Inactivos</span>
              <strong className="stat-card__value">{totals.inactive}</strong>
            </div>
          </div>
          <div className="stat-card stat-card--alert">
            <ShieldAlert size={18} aria-hidden="true" />
            <div>
              <span className="stat-card__label">Bloqueados</span>
              <strong className="stat-card__value">{totals.locked}</strong>
            </div>
          </div>
        </div>
        <div className="user-dashboard__columns">
          <div className="user-dashboard__column">
            <div className="user-dashboard__column-title">
              <Activity size={16} aria-hidden="true" />
              <h4>Actividad reciente</h4>
            </div>
            {recentActivity.length === 0 ? (
              <p className="muted-text">Sin movimientos relevantes en las últimas horas.</p>
            ) : (
              <ul className="user-dashboard__list">
                {recentActivity.map((item) => (
                  <li key={item.id}>
                    <div className={`badge badge-${item.severity}`} aria-label={`Severidad ${item.severity}`} />
                    <div>
                      <p className="user-dashboard__list-title">{item.action}</p>
                      <p className="user-dashboard__list-meta">
                        {formatDateTime(item.created_at)} · {item.performed_by_name ?? "Sistema"}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="user-dashboard__column">
            <div className="user-dashboard__column-title">
              <UsersIcon size={16} aria-hidden="true" />
              <h4>Sesiones activas</h4>
            </div>
            {recentSessions.length === 0 ? (
              <p className="muted-text">No hay sesiones corporativas activas.</p>
            ) : (
              <ul className="user-dashboard__list">
                {recentSessions.map((session) => (
                  <li key={session.session_id}>
                    <div className={`status-indicator status-${session.status}`} aria-hidden="true" />
                    <div>
                      <p className="user-dashboard__list-title">{session.username}</p>
                      <p className="user-dashboard__list-meta">
                        Inicio: {formatDateTime(session.created_at)}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="user-dashboard__column">
            <div className="user-dashboard__column-title">
              <ShieldAlert size={16} aria-hidden="true" />
              <h4>Alertas</h4>
            </div>
            {alerts ? (
              <div className="user-dashboard__alerts">
                <p><strong>Críticas:</strong> {alerts.critical}</p>
                <p><strong>Preventivas:</strong> {alerts.warning}</p>
                <p><strong>Informativas:</strong> {alerts.info}</p>
                <p><strong>Pendientes:</strong> {alerts.pending_count}</p>
              </div>
            ) : (
              <p className="muted-text">Sin alertas registradas.</p>
            )}
          </div>
        </div>
      </div>
      <LoadingOverlay visible={loading} label="Sincronizando panel de seguridad..." />
    </section>
  );
}

type RolePermissionsMatrixProps = {
  roles: RolePermissionMatrix[];
  selectedRole: string;
  permissions: RoleModulePermission[];
  onSelectRole: (role: string) => void;
  onToggle: (module: string, field: keyof RoleModulePermission) => void;
  onReset: () => void;
  onSave: () => void;
  saving: boolean;
  loading: boolean;
  hasChanges: boolean;
};

function RolePermissionsMatrix({
  roles,
  selectedRole,
  permissions,
  onSelectRole,
  onToggle,
  onReset,
  onSave,
  saving,
  loading,
  hasChanges,
}: RolePermissionsMatrixProps) {
  return (
    <section className="permissions-panel card-section">
      <header className="permissions-panel__header">
        <div>
          <h3>Permisos por rol</h3>
          <p className="card-subtitle">Controla la matriz de acceso a módulos sensibles</p>
        </div>
        <select value={selectedRole} onChange={(event) => onSelectRole(event.target.value)}>
          {roles.map((role) => (
            <option key={role.role} value={role.role}>
              {role.role}
            </option>
          ))}
        </select>
      </header>
      {loading ? (
        <LoadingOverlay visible label="Cargando permisos corporativos..." />
      ) : permissions.length === 0 ? (
        <p className="muted-text">No hay permisos registrados para este rol.</p>
      ) : (
        <div className="permissions-table-wrapper">
          <table className="permissions-table">
            <thead>
              <tr>
                <th>Módulo</th>
                <th>Ver</th>
                <th>Editar</th>
                <th>Eliminar</th>
              </tr>
            </thead>
            <tbody>
              {permissions.map((permission) => (
                <tr key={permission.module}>
                  <td className="permissions-table__module">{permission.module}</td>
                  {["can_view", "can_edit", "can_delete"].map((field) => (
                    <td key={field}>
                      <label className="checkbox-control">
                        <input
                          type="checkbox"
                          checked={permission[field as keyof RoleModulePermission] as boolean}
                          onChange={() => onToggle(permission.module, field as keyof RoleModulePermission)}
                        />
                        <span />
                      </label>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="permissions-actions">
        <button type="button" className="button button-secondary" onClick={onReset} disabled={!hasChanges || saving}>
          Restablecer
        </button>
        <button type="button" className="button button-primary" onClick={onSave} disabled={!hasChanges || saving}>
          {saving ? "Guardando..." : "Guardar"}
        </button>
      </div>
    </section>
  );
}

type UserFormProps = {
  mode: "create" | "edit";
  values: FormState;
  onChange: (patch: Partial<FormState>) => void;
  onSubmit: () => void;
  onReset: () => void;
  roles: Role[];
  stores: Store[];
  saving: boolean;
  disabled?: boolean;
};

function UserForm({ mode, values, onChange, onSubmit, onReset, roles, stores, saving, disabled }: UserFormProps) {
  const isCreate = mode === "create";
  const handleCheckboxChange = (roleName: string) => {
    if (!isCreate) {
      return;
    }
    const nextRoles = values.roles.includes(roleName)
      ? values.roles.filter((value) => value !== roleName)
      : [...values.roles, roleName];
    onChange({ roles: nextRoles });
  };

  return (
    <section className="user-form card-section">
      <header className="user-form__header">
        <h3>{isCreate ? "Crear usuario" : "Editar usuario"}</h3>
        <p className="card-subtitle">
          {isCreate
            ? "Registra colaboradores con roles corporativos y sucursal asignada"
            : "Actualiza datos de contacto y credenciales corporativas"}
        </p>
      </header>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
        className="user-form__body"
      >
        <div className="user-form__row">
          <label>
            <span>Correo corporativo</span>
            <input
              type="email"
              value={values.username}
              onChange={(event) => onChange({ username: event.target.value })}
              placeholder="usuario@softmobile"
              required={isCreate}
              disabled={!isCreate || disabled || saving}
            />
          </label>
          <label>
            <span>Nombre completo</span>
            <input
              type="text"
              value={values.fullName}
              onChange={(event) => onChange({ fullName: event.target.value })}
              placeholder="Nombre y apellidos"
              disabled={disabled || saving}
            />
          </label>
        </div>
        <div className="user-form__row">
          <label>
            <span>Teléfono</span>
            <input
              type="tel"
              value={values.telefono}
              onChange={(event) => onChange({ telefono: event.target.value })}
              placeholder="+52 55 0000 0000"
              disabled={disabled || saving}
            />
          </label>
          <label>
            <span>{isCreate ? "Contraseña inicial" : "Nueva contraseña (opcional)"}</span>
            <input
              type="password"
              value={values.password}
              onChange={(event) => onChange({ password: event.target.value })}
              placeholder={isCreate ? "Mínimo 8 caracteres" : "Dejar vacío para conservar la actual"}
              required={isCreate}
              minLength={isCreate ? 8 : undefined}
              disabled={disabled || saving}
            />
          </label>
        </div>
        <div className="user-form__row">
          <label>
            <span>Sucursal</span>
            <select
              value={values.storeId === "none" ? "none" : String(values.storeId)}
              onChange={(event) => {
                const selected = event.target.value === "none" ? "none" : Number(event.target.value);
                onChange({ storeId: selected });
              }}
              disabled={disabled || saving}
            >
              <option value="none">Sin sucursal</option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="user-form__row">
          <fieldset className="user-form__roles" disabled={disabled || saving}>
            <legend>Roles asignados</legend>
            {isCreate ? (
              <div className="role-checkboxes">
                {roles.map((role) => (
                  <label key={role.id} className="checkbox-control checkbox-control--inline">
                    <input
                      type="checkbox"
                      checked={values.roles.includes(role.name)}
                      onChange={() => handleCheckboxChange(role.name)}
                    />
                    <span />
                    <span>{role.name}</span>
                  </label>
                ))}
              </div>
            ) : (
              <p className="muted-text">Gestiona los roles desde la tabla inferior utilizando los checkboxes por módulo.</p>
            )}
          </fieldset>
        </div>
        <div className="user-form__actions">
          <button type="button" className="button button-secondary" onClick={onReset} disabled={saving}>
            {isCreate ? "Limpiar" : "Cancelar"}
          </button>
          <button type="submit" className="button button-primary" disabled={saving}>
            {saving ? "Guardando..." : isCreate ? "Registrar usuario" : "Guardar cambios"}
          </button>
        </div>
      </form>
    </section>
  );
}

function UserManagement({ token }: Props) {
  const { pushToast, currentUser } = useUsersModule();
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [dashboard, setDashboard] = useState<UserDashboardMetrics | null>(null);
  const [permissionsMatrix, setPermissionsMatrix] = useState<RolePermissionMatrix[]>([]);
  const [permissionDraft, setPermissionDraft] = useState<Record<string, RoleModulePermission[]>>({});
  const [selectedRole, setSelectedRole] = useState<string>("OPERADOR");
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [formState, setFormState] = useState<FormState>(DEFAULT_FORM_STATE);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("TODOS");
  const [statusFilter, setStatusFilter] = useState<UserQueryFilters["status"]>("all");
  const [storeFilter, setStoreFilter] = useState<number | "ALL">("ALL");
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingDashboard, setLoadingDashboard] = useState(false);
  const [loadingPermissions, setLoadingPermissions] = useState(false);
  const [savingPermissions, setSavingPermissions] = useState(false);
  const [savingUser, setSavingUser] = useState(false);
  const [exporting, setExporting] = useState<"pdf" | "xlsx" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const debouncedSearch = useMemo(() => search.trim(), [search]);

  const filtersForQuery = useMemo<UserQueryFilters>(() => {
    const filters: UserQueryFilters = { status: statusFilter };
    if (debouncedSearch) {
      filters.search = debouncedSearch;
    }
    if (roleFilter !== "TODOS") {
      filters.role = roleFilter;
    }
    if (storeFilter !== "ALL") {
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
        error_ instanceof Error
          ? error_.message
          : "No fue posible cargar el panel de seguridad.";
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
      if (data.length > 0) {
        const defaultRole = data.find((item) => item.role === selectedRole)?.role ?? data[0].role;
        setSelectedRole(defaultRole);
        const mapping: Record<string, RoleModulePermission[]> = {};
        data.forEach((item) => {
          mapping[item.role] = item.permissions.map((permission) => ({ ...permission }));
        });
        setPermissionDraft(mapping);
      }
    } catch (error_) {
      const message =
        error_ instanceof Error ? error_.message : "No fue posible cargar los permisos corporativos.";
      pushToast({ message, variant: "error" });
    } finally {
      setLoadingPermissions(false);
    }
  }, [token, pushToast, selectedRole]);

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
          error_ instanceof Error ? error_.message : "No fue posible cargar los catálogos de seguridad.";
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
        error_ instanceof Error ? error_.message : "No fue posible actualizar la lista de usuarios.";
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
        error_ instanceof Error ? error_.message : "No fue posible actualizar los roles del usuario.";
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
        error_ instanceof Error ? error_.message : "No fue posible actualizar el estado del usuario.";
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
        setUsers((current) => current.map((item) => (item.id === selectedUser.id ? updated : item)));
        pushToast({ message: `Usuario ${updated.username} actualizado correctamente`, variant: "success" });
        setSelectedUserId(updated.id);
        void loadDashboard();
      } catch (error_) {
        const message =
          error_ instanceof Error ? error_.message : "No fue posible actualizar la cuenta corporativa.";
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
      full_name: formState.fullName.trim() || undefined,
      telefono: formState.telefono.trim() || undefined,
      roles: formState.roles,
      store_id: formState.storeId === "none" ? undefined : formState.storeId,
    };

    try {
      setSavingUser(true);
      const created = await usersService.createUser(token, payload);
      pushToast({ message: `Usuario ${created.username} creado correctamente`, variant: "success" });
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
      pushToast({ message: `Reporte ${format.toUpperCase()} generado correctamente`, variant: "success" });
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
    return permissionDraft[selectedRole] ?? baselinePermissions.map((permission) => ({ ...permission }));
  }, [permissionDraft, selectedRole, baselinePermissions]);

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
      const permissions = current[selectedRole] ?? baselinePermissions.map((permission) => ({ ...permission }));
      const updated = permissions.map((permission) =>
        permission.module === module
          ? { ...permission, [field]: !permission[field] }
          : permission,
      );
      return { ...current, [selectedRole]: updated };
    });
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
      const updated = await usersService.updateRolePermissions(token, selectedRole, currentPermissions, reason);
      setPermissionsMatrix((current) => {
        const filtered = current.filter((item) => item.role !== updated.role);
        return [...filtered, updated].sort((a, b) => a.role.localeCompare(b.role));
      });
      setPermissionDraft((current) => ({
        ...current,
        [updated.role]: updated.permissions.map((permission) => ({ ...permission })),
      }));
      pushToast({ message: `Permisos actualizados para ${updated.role}`, variant: "success" });
    } catch (error_) {
      const message =
        error_ instanceof Error ? error_.message : "No fue posible actualizar los permisos del rol.";
      pushToast({ message, variant: "error" });
    } finally {
      setSavingPermissions(false);
    }
  };

  const roleNames = useMemo(() => roles.map((role) => role.name), [roles]);

  return (
    <section className="card user-management">
      <header className="card-header">
        <div>
          <h2>Gestión de usuarios</h2>
          <p className="card-subtitle">
            Administra cuentas corporativas, roles asignados, motivos de inactivación y permisos por módulo.
          </p>
        </div>
        <div className="export-buttons">
          <button
            type="button"
            className="button button-secondary"
            onClick={() => handleExport("pdf")}
            disabled={exporting !== null}
          >
            <FileText size={16} aria-hidden="true" />
            PDF
          </button>
          <button
            type="button"
            className="button button-secondary"
            onClick={() => handleExport("xlsx")}
            disabled={exporting !== null}
          >
            <FileSpreadsheet size={16} aria-hidden="true" />
            Excel
          </button>
        </div>
      </header>
      {error ? <p className="error-text">{error}</p> : null}
      <UserDashboardPanel dashboard={dashboard} loading={loadingDashboard} onRefresh={loadDashboard} />
      <div className="user-management__content">
        <div className="user-management__main">
          <div className="user-filters">
            <label>
              <span>Búsqueda</span>
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Correo o nombre completo"
              />
            </label>
            <label>
              <span>Rol</span>
              <select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)}>
                <option value="TODOS">Todos</option>
                {roleNames.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Estado</span>
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}>
                <option value="all">Todos</option>
                <option value="active">Activos</option>
                <option value="inactive">Inactivos</option>
              </select>
            </label>
            <label>
              <span>Sucursal</span>
              <select
                value={storeFilter === "ALL" ? "ALL" : String(storeFilter)}
                onChange={(event) =>
                  setStoreFilter(event.target.value === "ALL" ? "ALL" : Number(event.target.value))
                }
              >
                <option value="ALL">Todas</option>
                {stores.map((store) => (
                  <option key={store.id} value={store.id}>
                    {store.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {loadingUsers ? <LoadingOverlay visible label="Cargando usuarios..." /> : null}
          {users.length === 0 && !loadingUsers ? (
            <p className="muted-text">No hay usuarios que coincidan con los filtros aplicados.</p>
          ) : (
            <div className="user-table-wrapper">
              <table className="user-table">
                <thead>
                  <tr>
                    <th>Usuario</th>
                    <th>Nombre</th>
                    <th>Sucursal</th>
                    <th>Estado</th>
                    <th>Activo</th>
                    {roleNames.map((role) => (
                      <th key={role}>{role}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr
                      key={user.id}
                      className={selectedUserId === user.id ? "is-selected" : undefined}
                      onClick={() => setSelectedUserId(user.id)}
                    >
                      <td>{user.username}</td>
                      <td>{user.full_name ?? "—"}</td>
                      <td>{user.store_name ?? "—"}</td>
                      <td>{user.estado}</td>
                      <td>
                        <label className="toggle-control" onClick={(event) => event.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={user.is_active}
                            onChange={(event) => handleStatusToggle(user, event.target.checked)}
                            disabled={currentUser?.id === user.id}
                          />
                          <span className="toggle-slider" />
                        </label>
                      </td>
                      {roleNames.map((roleName) => {
                        const hasRole = user.roles.some((role) => role.name === roleName);
                        return (
                          <td key={`${user.id}-${roleName}`}>
                            <label className="checkbox-control" onClick={(event) => event.stopPropagation()}>
                              <input
                                type="checkbox"
                                checked={hasRole}
                                onChange={(event) => handleRoleToggle(user, roleName, event.target.checked)}
                                disabled={currentUser?.id === user.id}
                              />
                              <span />
                            </label>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        <div className="user-management__aside">
          <UserForm
            mode={selectedUser ? "edit" : "create"}
            values={formState}
            onChange={(patch) => setFormState((current) => ({ ...current, ...patch }))}
            onSubmit={handleFormSubmit}
            onReset={() => {
              setSelectedUserId(null);
              setFormState(DEFAULT_FORM_STATE);
            }}
            roles={roles}
            stores={stores}
            saving={savingUser}
          />
          <RolePermissionsMatrix
            roles={permissionsMatrix.sort((a, b) => a.role.localeCompare(b.role))}
            selectedRole={selectedRole}
            permissions={currentPermissions}
            onSelectRole={(role) => {
              setSelectedRole(role);
            }}
            onToggle={handlePermissionToggle}
            onReset={handlePermissionReset}
            onSave={handlePermissionSave}
            saving={savingPermissions}
            loading={loadingPermissions}
            hasChanges={hasPermissionChanges}
          />
        </div>
      </div>
    </section>
  );
}

export default UserManagement;
