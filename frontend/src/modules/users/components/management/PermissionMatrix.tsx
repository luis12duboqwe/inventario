import type { RoleModulePermission, RolePermissionMatrix } from "../../../../api";
import LoadingOverlay from "../../../../shared/components/LoadingOverlay";

export type PermissionMatrixProps = {
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

function PermissionMatrix({
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
}: PermissionMatrixProps) {
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
                          onChange={() =>
                            onToggle(permission.module, field as keyof RoleModulePermission)
                          }
                          aria-label={`${field} en ${permission.module}`}
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
        <button
          type="button"
          className="button button-secondary"
          onClick={onReset}
          disabled={!hasChanges || saving}
        >
          Restablecer
        </button>
        <button
          type="button"
          className="button button-primary"
          onClick={onSave}
          disabled={!hasChanges || saving}
        >
          {saving ? "Guardando..." : "Guardar"}
        </button>
      </div>
    </section>
  );
}

export default PermissionMatrix;
