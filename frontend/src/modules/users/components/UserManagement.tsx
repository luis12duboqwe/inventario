import { useEffect, useMemo, useState } from "react";
import {
  listRoles,
  listUsers,
  updateUserRoles,
  updateUserStatus,
  type Role,
  type UserAccount,
} from "../../../api";
import { useUsersModule } from "../hooks/useUsersModule";
import LoadingOverlay from "../../../components/LoadingOverlay";

type Props = {
  token: string;
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("TODOS");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");

  const roleNames = useMemo(() => roles.map((role) => role.name), [roles]);

  const filteredUsers = useMemo(() => {
    const normalizedQuery = search.trim().toLowerCase();
    return users.filter((user) => {
      const matchesQuery =
        !normalizedQuery ||
        [user.username, user.full_name].some((value) =>
          value ? value.toLowerCase().includes(normalizedQuery) : false,
        );
      const matchesRole =
        roleFilter === "TODOS" || user.roles.some((role) => role.name === roleFilter);
      const matchesStatus =
        statusFilter === "all" || (statusFilter === "active" ? user.is_active : !user.is_active);
      return matchesQuery && matchesRole && matchesStatus;
    });
  }, [roleFilter, search, statusFilter, users]);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const [usersData, rolesData] = await Promise.all([listUsers(token), listRoles(token)]);
        setUsers(usersData);
        setRoles(rolesData);
      } catch (err) {
        const message = err instanceof Error ? err.message : "No fue posible cargar la lista de usuarios";
        setError(message);
        pushToast({ message, variant: "error" });
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [token]);

  const toggleRole = async (user: UserAccount, roleName: string, checked: boolean) => {
    const reason = ensureReason();
    if (!reason) {
      pushToast({ message: "Operación cancelada: motivo inválido", variant: "info" });
      return;
    }
    setUpdatingId(user.id);
    try {
      const currentRoles = user.roles.map((role) => role.name);
      const updatedRoles = checked
        ? Array.from(new Set([...currentRoles, roleName]))
        : currentRoles.filter((role) => role !== roleName);
      const updated = await updateUserRoles(token, user.id, updatedRoles, reason);
      setUsers((current) => current.map((item) => (item.id === user.id ? updated : item)));
      pushToast({ message: `Roles actualizados para ${user.username}`, variant: "success" });
    } catch (err) {
      pushToast({
        message: err instanceof Error ? err.message : "No fue posible actualizar los roles",
        variant: "error",
      });
    } finally {
      setUpdatingId(null);
    }
  };

  const toggleStatus = async (user: UserAccount, isActive: boolean) => {
    const reason = ensureReason();
    if (!reason) {
      pushToast({ message: "Operación cancelada: motivo inválido", variant: "info" });
      return;
    }
    setUpdatingId(user.id);
    try {
      const updated = await updateUserStatus(token, user.id, isActive, reason);
      setUsers((current) => current.map((item) => (item.id === user.id ? updated : item)));
      pushToast({
        message: `Estado actualizado para ${user.username}`,
        variant: "success",
      });
    } catch (err) {
      pushToast({
        message: err instanceof Error ? err.message : "No fue posible actualizar el estado",
        variant: "error",
      });
    } finally {
      setUpdatingId(null);
    }
  };

  const isEditingSelf = (userId: number) => currentUser?.id === userId;

  return (
    <section className="card user-management">
      <header className="card-header">
        <div>
          <h2>Gestión de usuarios</h2>
          <p className="card-subtitle">
            Asigna roles corporativos, habilita o suspende accesos y controla permisos con checkboxes.
          </p>
        </div>
        {loading ? <span className="pill neutral">Sincronizando…</span> : null}
      </header>
      {error ? <p className="error-text">{error}</p> : null}
      <div className="user-filters">
        <label>
          <span>Búsqueda</span>
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Usuario o nombre completo"
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
      </div>
      <LoadingOverlay visible={loading} label="Cargando usuarios..." />
      {filteredUsers.length === 0 && !loading ? (
        <p className="muted-text">No hay usuarios que coincidan con los filtros seleccionados.</p>
      ) : (
        <div className="user-table-wrapper">
          <table className="user-table">
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Nombre</th>
                <th>Activo</th>
                {roleNames.map((role) => (
                  <th key={role}>{role}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((user) => (
                <tr key={user.id}>
                  <td>{user.username}</td>
                  <td>{user.full_name ?? "—"}</td>
                  <td>
                    <label className="toggle-control">
                      <input
                        type="checkbox"
                        checked={user.is_active}
                        onChange={(event) => toggleStatus(user, event.target.checked)}
                        disabled={updatingId === user.id || isEditingSelf(user.id)}
                      />
                      <span className="toggle-slider" />
                    </label>
                  </td>
                  {roleNames.map((roleName) => {
                    const hasRole = user.roles.some((role) => role.name === roleName);
                    return (
                      <td key={`${user.id}-${roleName}`}>
                        <label className="checkbox-control">
                          <input
                            type="checkbox"
                            checked={hasRole}
                            onChange={(event) => toggleRole(user, roleName, event.target.checked)}
                            disabled={updatingId === user.id}
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
    </section>
  );
}

export default UserManagement;
