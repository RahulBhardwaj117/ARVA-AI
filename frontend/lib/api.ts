import type {
  ApiErrorPayload,
  HealthResponse,
  TokenResponse,
  User,
} from "./types";
import type { LoginInput } from "./schemas";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly status: number,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  token?: string,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...init.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
  } catch {
    throw new ApiError(
      "The ARVA API is unavailable. Start the local platform and try again.",
      "API_UNAVAILABLE",
      0,
    );
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ApiErrorPayload | null;
    throw new ApiError(
      payload?.error.message ?? "The request could not be completed.",
      payload?.error.code ?? "REQUEST_FAILED",
      response.status,
      payload?.error.request_id,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function login(input: LoginInput): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function logout(): Promise<void> {
  await apiRequest<unknown>("/api/v1/auth/logout", { method: "POST" });
}

export function getCurrentUser(token: string): Promise<User> {
  return apiRequest<User>("/api/v1/auth/me", {}, token);
}

export function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health");
}

export function getReadiness(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/ready");
}

export function getPlatformData<T>(path: string, token: string): Promise<T> {
  return apiRequest<T>(`/api/v1${path}`, {}, token);
}

export function postPlatformAction<T>(
  path: string,
  token: string,
  body: Record<string, unknown> = {},
): Promise<T> {
  return apiRequest<T>(
    `/api/v1${path}`,
    { method: "POST", body: JSON.stringify(body) },
    token,
  );
}

export function patchPlatformAction<T>(
  path: string,
  token: string,
  body?: Record<string, unknown>,
): Promise<T> {
  const hasBody = body && Object.keys(body).length > 0;
  return apiRequest<T>(
    `/api/v1${path}`,
    {
      method: "PATCH",
      ...(hasBody ? { body: JSON.stringify(body) } : {}),
    },
    token,
  );
}
