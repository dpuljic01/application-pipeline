// Mirrors backend/app/domain/enums.py and backend/app/api/schemas/application.py.
// No codegen step in this pass — keep these in sync by hand if the backend changes.

export const APPLICATION_STAGES = [
  "SAVED",
  "APPLIED",
  "INTERVIEW",
  "OFFER",
  "ACCEPTED",
  "REJECTED",
  "WITHDRAWN",
  "GHOSTED",
] as const;

export type ApplicationStage = (typeof APPLICATION_STAGES)[number];

// Mirrors ALLOWED_TRANSITIONS in backend/app/domain/enums.py
export const ALLOWED_TRANSITIONS: Record<ApplicationStage, ApplicationStage[]> = {
  SAVED: ["APPLIED", "WITHDRAWN"],
  APPLIED: ["INTERVIEW", "REJECTED", "WITHDRAWN", "GHOSTED"],
  INTERVIEW: ["OFFER", "REJECTED", "WITHDRAWN", "GHOSTED"],
  OFFER: ["ACCEPTED", "REJECTED", "WITHDRAWN"],
  REJECTED: [],
  WITHDRAWN: [],
  ACCEPTED: [],
  GHOSTED: [],
};

export interface Application {
  id: string;
  company: string;
  role_title: string;
  job_url: string | null;
  location: string | null;
  salary_range: string | null;
  stage: ApplicationStage;
  created_at: string;
  updated_at: string;
  last_activity_at: string | null;
  stage_changed_at: string | null;
}

export interface ApplicationCreateInput {
  company: string;
  role_title: string;
  job_url?: string | null;
  location?: string | null;
  salary_range?: string | null;
}

export interface ApplicationUpdateInput {
  company?: string;
  role_title?: string;
  job_url?: string | null;
  location?: string | null;
  salary_range?: string | null;
  stage_changed_at?: string | null;
}
