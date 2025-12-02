import { getAuditLogs } from "@api/audit";
import {
  activateTotp,
  disableTotp,
  getTotpStatus,
  listActiveSessions,
  revokeSession,
  setupTotp,
} from "@api/security";
import type { AuditLogEntry } from "@api/audit";
import type { ActiveSession, TOTPSetup, TOTPStatus } from "@api/security";

export const securityService = {
  fetchAuditLogs: getAuditLogs,
  requestTotpSetup: setupTotp,
  activateTotp,
  disableTotp,
  getTotpStatus,
  listActiveSessions,
  revokeSession,
};

export type SecurityTotpState = {
  status: TOTPStatus | null;
  setup: TOTPSetup | null;
  sessions: ActiveSession[];
  logs: AuditLogEntry[];
};
