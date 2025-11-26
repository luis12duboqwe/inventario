// [PACK22-POS-PERMS-START]
import { PERMS, ROLE_MATRIX, type Role, type Perm } from "../../../auth/roles";

function hasPermission(role?: Role, perm?: Perm): boolean {
  if (!role || !perm) {
    return false;
  }
  const allowed = ROLE_MATRIX[role] ?? [];
  return allowed.includes(perm);
}

export function canApplyDiscount(role?: Role) {
  return hasPermission(role, PERMS.POS_DISCOUNT);
}

export function canOverridePrice(role?: Role) {
  return hasPermission(role, PERMS.POS_PRICE_OVERRIDE);
}
// [PACK22-POS-PERMS-END]
