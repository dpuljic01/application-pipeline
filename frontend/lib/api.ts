import type {
  Activity,
  ActivityCreateInput,
  Application,
  ApplicationCreateInput,
  ApplicationUpdateInput,
  ParsedJobDescription,
  Profile,
  ProfileUpdateInput,
  StageChangeInput,
} from "@/lib/types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

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

export function getApplication(
  token: string,
  applicationId: string,
): Promise<Application> {
  return request<Application>(`/applications/${applicationId}`, token);
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

export function updateApplication(
  token: string,
  applicationId: string,
  input: ApplicationUpdateInput,
): Promise<Application> {
  return request<Application>(`/applications/${applicationId}`, token, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function listActivities(
  token: string,
  applicationId: string,
): Promise<Activity[]> {
  return request<Activity[]>(`/applications/${applicationId}/activities`, token);
}

export function createActivity(
  token: string,
  applicationId: string,
  input: ActivityCreateInput,
): Promise<Activity> {
  return request<Activity>(`/applications/${applicationId}/activities`, token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function deleteApplication(
  token: string,
  applicationId: string,
): Promise<void> {
  return request<void>(`/applications/${applicationId}`, token, {
    method: "DELETE",
  });
}

export function parseJd(
  token: string,
  applicationId: string,
  jdText: string,
): Promise<ParsedJobDescription> {
  return request<ParsedJobDescription>(`/applications/${applicationId}/parse-jd`, token, {
    method: "POST",
    body: JSON.stringify({ jd_text: jdText }),
  });
}

export function scoreApplication(
  token: string,
  applicationId: string,
): Promise<Application> {
  return request<Application>(`/applications/${applicationId}/score`, token, {
    method: "POST",
  });
}

export function generateFollowUp(
  token: string,
  applicationId: string,
  context?: string,
): Promise<Application> {
  return request<Application>(`/applications/${applicationId}/generate-followup`, token, {
    method: "POST",
    body: JSON.stringify({ context: context || null }),
  });
}

export function getProfile(token: string): Promise<Profile> {
  return request<Profile>("/profile", token);
}

export function updateProfile(
  token: string,
  input: ProfileUpdateInput,
): Promise<Profile> {
  return request<Profile>("/profile", token, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function changeApplicationStage(
  token: string,
  applicationId: string,
  input: StageChangeInput,
): Promise<Application> {
  return request<Application>(`/applications/${applicationId}/stage`, token, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}
