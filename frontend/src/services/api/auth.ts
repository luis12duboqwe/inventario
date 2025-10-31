import type {
  AuthProfile,
  AuthSession,
  BootstrapRequest,
  BootstrapStatus,
  Credentials,
  UserAccount,
} from "../../api";
import httpClient, {
  UNAUTHORIZED_EVENT,
  clearAuthToken,
  setAuthToken,
} from "./http";

export { UNAUTHORIZED_EVENT };

export async function getBootstrapStatus(): Promise<BootstrapStatus> {
  const response = await httpClient.get<BootstrapStatus>("/auth/bootstrap/status");
  return response.data;
}

export async function bootstrapAdmin(payload: BootstrapRequest): Promise<UserAccount> {
  const body: Record<string, unknown> = {
    username: payload.username,
    password: payload.password,
    roles: [],
  };

  if (payload.full_name) {
    body.full_name = payload.full_name;
  }

  if (payload.telefono) {
    body.telefono = payload.telefono;
  }

  const response = await httpClient.post<UserAccount>("/auth/bootstrap", body);
  return response.data;
}

// [PACK28-auth-service]
export async function login(credentials: Credentials): Promise<AuthSession> {
  const payload: Record<string, string> = {
    username: credentials.username,
    password: credentials.password,
  };
  if (credentials.otp) {
    payload.otp = credentials.otp;
  }
  const response = await httpClient.post<AuthSession>("/auth/login", payload);
  setAuthToken(response.data.access_token);
  return response.data;
}

// [PACK28-auth-service]
export async function refreshAccessToken(): Promise<AuthSession | null> {
  try {
    const response = await httpClient.post<AuthSession>("/auth/refresh", {});
    const session = response.data;
    if (session?.access_token) {
      setAuthToken(session.access_token);
      return session;
    }
    clearAuthToken();
    return null;
  } catch (error) {
    clearAuthToken();
    throw error;
  }
}

// [PACK28-auth-service]
export async function getCurrentUser(): Promise<AuthProfile> {
  const response = await httpClient.get<AuthProfile>("/auth/me");
  return response.data;
}

export function logout(): void {
  clearAuthToken();
}

export type {
  AuthProfile,
  AuthSession,
  Credentials,
  BootstrapStatus,
  BootstrapRequest,
  UserAccount,
} from "../../api";
