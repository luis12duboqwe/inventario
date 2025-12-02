import type { Role, Store, RoleModulePermission, RolePermissionMatrix } from "../../../../api";
import type { UserFormState } from "./types";
import PermissionMatrix from "./PermissionMatrix";

export type SidePanelProps = {
  mode: "create" | "edit";
  formValues: UserFormState;
  onFormChange: (patch: Partial<UserFormState>) => void;
  onFormSubmit: () => void;
  onFormReset: () => void;
  roles: Role[];
  stores: Store[];
  savingUser: boolean;
  disableForm?: boolean;
  permissionsMatrix: RolePermissionMatrix[];
  selectedRole: string;
  permissions: RoleModulePermission[];
  onSelectRole: (role: string) => void;
  onTogglePermission: (module: string, field: keyof RoleModulePermission) => void;
  onResetPermissions: () => void;
  onSavePermissions: () => void;
  savingPermissions: boolean;
  loadingPermissions: boolean;
  hasPermissionChanges: boolean;
  onOpenRoleModal?: () => void;
};

function SidePanel({
  mode,
  formValues,
  onFormChange,
  onFormSubmit,
  onFormReset,
  roles,
  stores,
  savingUser,
  disableForm = false,
  permissionsMatrix,
  selectedRole,
  permissions,
  onSelectRole,
  onTogglePermission,
  onResetPermissions,
  onSavePermissions,
  savingPermissions,
  loadingPermissions,
  hasPermissionChanges,
  onOpenRoleModal,
}: SidePanelProps) {
  const isCreate = mode === "create";

  const handleRoleCheckboxChange = (roleName: string) => {
    if (!isCreate) {
      return;
    }
    const nextRoles = formValues.roles.includes(roleName)
      ? formValues.roles.filter((value) => value !== roleName)
      : [...formValues.roles, roleName];
    onFormChange({ roles: nextRoles });
  };

  return (
    <div className="user-management__aside">
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
            onFormSubmit();
          }}
          className="user-form__body"
        >
          <div className="user-form__row">
            <label>
              <span>Correo corporativo</span>
              <input
                type="email"
                value={formValues.username}
                onChange={(event) => onFormChange({ username: event.target.value })}
                placeholder="usuario@softmobile"
                required={isCreate}
                disabled={!isCreate || disableForm || savingUser}
              />
            </label>
            <label>
              <span>Nombre completo</span>
              <input
                type="text"
                value={formValues.fullName}
                onChange={(event) => onFormChange({ fullName: event.target.value })}
                placeholder="Nombre y apellidos"
                disabled={disableForm || savingUser}
              />
            </label>
          </div>
          <div className="user-form__row">
            <label>
              <span>Teléfono</span>
              <input
                type="tel"
                value={formValues.telefono}
                onChange={(event) => onFormChange({ telefono: event.target.value })}
                placeholder="+52 55 0000 0000"
                disabled={disableForm || savingUser}
              />
            </label>
            <label>
              <span>{isCreate ? "Contraseña inicial" : "Nueva contraseña (opcional)"}</span>
              <input
                type="password"
                value={formValues.password}
                onChange={(event) => onFormChange({ password: event.target.value })}
                placeholder={
                  isCreate ? "Mínimo 8 caracteres" : "Dejar vacío para conservar la actual"
                }
                required={isCreate}
                minLength={isCreate ? 8 : undefined}
                disabled={disableForm || savingUser}
              />
            </label>
          </div>
          <div className="user-form__row">
            <label>
              <span>Sucursal</span>
              <select
                value={formValues.storeId === "none" ? "none" : String(formValues.storeId)}
                onChange={(event) => {
                  const selected =
                    event.target.value === "none" ? "none" : Number(event.target.value);
                  onFormChange({ storeId: selected });
                }}
                disabled={disableForm || savingUser}
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
            <fieldset className="user-form__roles" disabled={disableForm || savingUser}>
              <legend>Roles asignados</legend>
              {isCreate ? (
                <div className="role-checkboxes">
                  {roles.map((role) => (
                    <label key={role.id} className="checkbox-control checkbox-control--inline">
                      <input
                        type="checkbox"
                        checked={formValues.roles.includes(role.name)}
                        onChange={() => handleRoleCheckboxChange(role.name)}
                      />
                      <span />
                      <span>{role.name}</span>
                    </label>
                  ))}
                </div>
              ) : (
                <p className="muted-text">
                  Gestiona los roles desde la tabla inferior utilizando los checkboxes por módulo.
                </p>
              )}
            </fieldset>
          </div>
          <div className="user-form__actions">
            <button
              type="button"
              className="button button-secondary"
              onClick={onFormReset}
              disabled={savingUser}
            >
              {isCreate ? "Limpiar" : "Cancelar"}
            </button>
            <button type="submit" className="button button-primary" disabled={savingUser}>
              {savingUser ? "Guardando..." : isCreate ? "Registrar usuario" : "Guardar cambios"}
            </button>
          </div>
        </form>
      </section>
      <PermissionMatrix
        roles={permissionsMatrix}
        selectedRole={selectedRole}
        permissions={permissions}
        onSelectRole={onSelectRole}
        onToggle={onTogglePermission}
        onReset={onResetPermissions}
        onSave={onSavePermissions}
        saving={savingPermissions}
        loading={loadingPermissions}
        hasChanges={hasPermissionChanges}
      />
      {onOpenRoleModal ? (
        <div className="permissions-actions">
          <button type="button" className="button button-secondary" onClick={onOpenRoleModal}>
            Ver matriz en modal
          </button>
        </div>
      ) : null}
    </div>
  );
}

export default SidePanel;
