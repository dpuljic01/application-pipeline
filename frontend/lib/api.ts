import type { Application, ApplicationCreateInput, ApplicationStage } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  token: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? `Request failed (${res.status})`);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export function listApplications(token: string): Promise<Application[]> {
  return request<Application[]>("/applications", token);
}

export function createApplication(
  token: string,
  input: ApplicationCreateInput,
): Promise<Application> {
  return request<Application>("/applications", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function changeApplicationStage(
  token: string,
  applicationId: string,
  stage: ApplicationStage,
): Promise<Application> {
  return request<Application>(`/applications/${applicationId}/stage`, token, {
    method: "PATCH",
    body: JSON.stringify({ stage }),
  });
}
