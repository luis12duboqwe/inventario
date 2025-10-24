import type { AxiosResponse } from "axios";
import type {
  BootstrapRequest,
  BootstrapStatus,
  Credentials,
  UserAccount,
} from "../../api";
import httpClient, {
  UNAUTHORIZED_EVENT,
  clearAuthToken,
  getAuthToken,
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

export async function login(credentials: Credentials): Promise<{ access_token: string }> {
  const formData = new URLSearchParams();
  formData.set("username", credentials.username);
  formData.set("password", credentials.password);

  const response: AxiosResponse<{ access_token: string }> = await httpClient.post(
    "/auth/token",
    formData,
    {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    },
  );

  setAuthToken(response.data.access_token);

  return response.data;
}

export async function getCurrentUser(): Promise<UserAccount> {
  const response = await httpClient.get<UserAccount>("/auth/me");
  return response.data;
}

export function logout(): void {
  clearAuthToken();
}

export function isAuthenticated(): boolean {
  return Boolean(getAuthToken());
}

export type { Credentials, BootstrapStatus, BootstrapRequest, UserAccount } from "../../api";
