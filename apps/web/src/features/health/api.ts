import { apiGet } from "@/lib/api-client";

export interface HealthCheckResponse {
  status: "ok";
  service: "local-drama-studio-api";
}

export function fetchHealth(): Promise<HealthCheckResponse> {
  return apiGet<HealthCheckResponse>("/api/health");
}
