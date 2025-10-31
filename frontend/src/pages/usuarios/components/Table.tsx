import type { UserAccount } from "../../../api";
import LoadingOverlay from "../../../shared/components/LoadingOverlay";

const formatDateTime = (value: string | null | undefined): string => {
  if (!value) {
    return "—";
  }
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return new Intl.DateTimeFormat("es-MX", { dateStyle: "short", timeStyle: "short" }).format(date);
  } catch {
    return value;
  }
};

const isUserLocked = (user: UserAccount): boolean => {
  if (!user.locked_until) {
    return false;
  }
  const lockedUntil = new Date(user.locked_until);
  if (Number.isNaN(lockedUntil.getTime())) {
    return false;
  }
  return lockedUntil.getTime() > Date.now();
};

export type UsersTableProps = {
  users: UserAccount[];
  roleNames: string[];
  selectedUserId: number | null;
  onSelectUser: (userId: number) => void;
  onToggleStatus: (user: UserAccount, active: boolean) => void;
  onToggleRole: (user: UserAccount, role: string, active: boolean) => void;
  currentUserId: number | null | undefined;
  loading: boolean;
};

function UsersTable({
  users,
  roleNames,
  selectedUserId,
  onSelectUser,
  onToggleStatus,
  onToggleRole,
  currentUserId,
  loading,
}: UsersTableProps) {
  return (
    <div className="user-table-section">
      {loading ? <LoadingOverlay visible label="Cargando usuarios..." /> : null}
      {users.length === 0 && !loading ? (
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
                <th>Bloqueado</th>
                {roleNames.map((role) => (
                  <th key={role}>{role}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((user) => {
                const locked = isUserLocked(user);
                const isCurrentUser = currentUserId === user.id;
                return (
                  <tr
                    key={user.id}
                    className={selectedUserId === user.id ? "is-selected" : undefined}
                    onClick={() => onSelectUser(user.id)}
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
                          onChange={(event) => onToggleStatus(user, event.target.checked)}
                          disabled={isCurrentUser}
                        />
                        <span className="toggle-slider" />
                      </label>
                    </td>
                    <td>
                      <span
                        className={`user-lock-indicator${
                          locked ? " user-lock-indicator--active" : " user-lock-indicator--clear"
                        }`}
                        title={locked ? `Bloqueado hasta ${formatDateTime(user.locked_until)}` : "Sin bloqueo activo"}
                      >
                        <span className="user-lock-indicator__dot" aria-hidden="true" />
                        {locked ? "Sí" : "No"}
                      </span>
                    </td>
                    {roleNames.map((roleName) => {
                      const hasRole = user.roles.some((role) => role.name === roleName);
                      return (
                        <td key={`${user.id}-${roleName}`}>
                          <label className="checkbox-control" onClick={(event) => event.stopPropagation()}>
                            <input
                              type="checkbox"
                              checked={hasRole}
                              onChange={(event) => onToggleRole(user, roleName, event.target.checked)}
                              disabled={isCurrentUser}
                            />
                            <span />
                          </label>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default UsersTable;
