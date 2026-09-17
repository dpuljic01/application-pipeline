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

// Mirrors backend/app/api/schemas/jd_parse.py — ParsedJobDescription
export type Seniority = "junior" | "mid" | "senior" | "staff";
export type SalaryConfidence = "stated" | "estimated" | "unknown";

export interface ParsedJobDescription {
  required_skills: string[];
  nice_to_have_skills: string[];
  seniority_claimed: string | null;
  seniority_assessed: Seniority;
  tech_stack: string[];
  languages: string[];
  years_experience_min: number | null;
  remote_policy: string | null;
  salary_range: string | null;
  salary_confidence: SalaryConfidence;
  key_responsibilities: string[];
  red_flags: string[];
  missing_info: string[];
  summary: string;
}

// Mirrors backend/app/api/schemas/match.py — MatchInsights, and the
// match_details dict shape assembled by backend/app/services/matcher.py.
export interface MatchInsights {
  fit_narrative: string;
  key_strengths: string[];
  gaps: string[];
  talking_points: string[];
}

export interface MatchComponentScore {
  score: number;
  max: number;
  [key: string]: unknown;
}

export interface MatchDetails {
  rule_score: number;
  components: Record<string, MatchComponentScore>;
  insights: MatchInsights;
  scored_at: string;
}

// Mirrors backend/app/api/schemas/followup.py — FollowUpEmail
export interface FollowUpEmail {
  subject: string;
  body: string;
}

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
  parsed_jd: ParsedJobDescription | null;
  match_score: number | null;
  match_details: MatchDetails | null;
  generated_followup: FollowUpEmail | null;
  last_followup_at: string | null;
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

// Mirrors backend/app/api/schemas/profile.py
export interface LanguageEntry {
  language: string;
  level: string;
}

export interface Profile {
  id: string;
  years_experience: number | null;
  skills: string[];
  languages: LanguageEntry[];
  target_seniorities: Seniority[];
  min_salary_chf: number | null;
  ideal_salary_chf: number | null;
  home_location: string | null;
}

export interface ProfileUpdateInput {
  years_experience?: number | null;
  skills?: string[];
  languages?: LanguageEntry[];
  target_seniorities?: Seniority[];
  min_salary_chf?: number | null;
  ideal_salary_chf?: number | null;
  home_location?: string | null;
}
