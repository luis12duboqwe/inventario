import { request, requestCollection } from "./client";

export type TOTPStatus = {
  is_active: boolean;
  activated_at?: string | null;
  last_verified_at?: string | null;
};

export type TOTPSetup = {
  secret: string;
  otpauth_url: string;
};

export type ReauthContext = {
  password: string;
  otp?: string;
};

function buildReauthHeaders(context?: ReauthContext): Record<string, string> {
  if (!context) return {};
  const headers: Record<string, string> = { "X-Reauth-Password": context.password };
  if (context.otp) {
    headers["X-Reauth-OTP"] = context.otp;
  }
  return headers;
}

export type ActiveSession = {
  id: number;
  user_id: number;
  session_token: string;
  created_at: string;
  last_used_at?: string | null;
  revoked_at?: string | null;
  revoked_by_id?: number | null;
  revoke_reason?: string | null;
};

export type SessionRevokeInput = {
  reason: string;
};

export function getTotpStatus(token: string): Promise<TOTPStatus> {
  return request<TOTPStatus>("/security/2fa/status", { method: "GET" }, token);
}

export function setupTotp(token: string, reason: string, reauth?: ReauthContext): Promise<TOTPSetup> {
  return request<TOTPSetup>(
    "/security/2fa/setup",
    { method: "POST", headers: { "X-Reason": reason, ...buildReauthHeaders(reauth) } },
    token
  );
}

export function activateTotp(
  token: string,
  code: string,
  reason: string,
  reauth?: ReauthContext,
): Promise<TOTPStatus> {
  return request<TOTPStatus>(
    "/security/2fa/activate",
    {
      method: "POST",
      body: JSON.stringify({ code }),
      headers: { "X-Reason": reason, ...buildReauthHeaders(reauth) },
    },
    token
  );
}

export function disableTotp(token: string, reason: string, reauth?: ReauthContext): Promise<void> {
  return request<void>(
    "/security/2fa/disable",
    { method: "POST", headers: { "X-Reason": reason, ...buildReauthHeaders(reauth) } },
    token
  );
}

export function listActiveSessions(token: string, userId?: number): Promise<ActiveSession[]> {
  const query = userId ? `?user_id=${userId}` : "";
  return requestCollection<ActiveSession>(`/security/sessions${query}`, { method: "GET" }, token);
}

export function revokeSession(
  token: string,
  sessionId: number,
  reason: string,
  reauth?: ReauthContext,
): Promise<ActiveSession> {
  return request<ActiveSession>(
    `/security/sessions/${sessionId}/revoke`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
      headers: { "X-Reason": reason, ...buildReauthHeaders(reauth) },
    },
    token
  );
}
