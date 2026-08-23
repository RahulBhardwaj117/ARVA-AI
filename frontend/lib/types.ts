export type DeploymentMode =
  | "simulation"
  | "recommendation"
  | "approval"
  | "controlled_autonomous";

export type UserRole =
  | "administrator"
  | "infrastructure_operator"
  | "ai_engineer"
  | "researcher"
  | "viewer"
  | "auditor";

export interface OrganizationSummary {
  id: string;
  name: string;
  slug: string;
  deployment_mode: DeploymentMode;
}

export interface User {
  id: string;
  organization_id: string;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  organization: OrganizationSummary;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
}

export interface HealthResponse {
  status: "healthy" | "ready";
  service: string;
  version: string;
  checks: Record<string, string> | null;
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    request_id: string;
  };
}

