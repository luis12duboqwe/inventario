import {
  activateTotp,
  disableTotp,
  getAuditLogs,
  getTotpStatus,
  listActiveSessions,
  revokeSession,
  setupTotp,
} from "../../../api";
import type { ActiveSession, AuditLogEntry, TOTPSetup, TOTPStatus } from "../../../api";

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
