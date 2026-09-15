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
  company_id: string | null;
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

// Mirrors ActivityType in backend/app/domain/enums.py
export const ACTIVITY_TYPES = [
  "NOTE",
  "OUTREACH",
  "FOLLOW_UP",
  "INTERVIEW",
  "OFFER",
  "REJECTION",
  "ACCEPTED",
  "GHOSTED",
  "STAGE_CHANGE",
] as const;

export type ActivityType = (typeof ACTIVITY_TYPES)[number];

// Auto-logged by the backend on every stage transition — not something a
// user picks when adding a note by hand.
export const MANUAL_ACTIVITY_TYPES = ACTIVITY_TYPES.filter(
  (type) => type !== "STAGE_CHANGE",
);

export interface Activity {
  id: string;
  application_id: string;
  activity_type: ActivityType;
  note: string | null;
  created_at: string;
  occurred_at: string;
}

export interface ActivityCreateInput {
  activity_type: ActivityType;
  note?: string | null;
  occurred_at?: string | null;
}
