// Helpers for picking a stage date with <input type="date"> (YYYY-MM-DD, in
// the user's local timezone) and turning it into the ISO datetime the API
// validates against [created_at, now].

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

// Local calendar date, not UTC - toISOString() would show yesterday/tomorrow
// near midnight for anyone not on UTC.
export function toDateInputValue(iso: string | Date): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function todayDateInputValue(): string {
  return toDateInputValue(new Date());
}

// Noon avoids the date rolling over across timezones, but a bare noon breaks
// the same-day cases: an application saved at 14:00 and applied to that day
// would be "before creation", and picking today before noon would be "in the
// future". Clamp into [createdAt, now] so any calendar day the user can pick
// maps to a timestamp the server accepts.
export function fromDateInputValue(value: string, createdAt: string): string {
  const noon = new Date(`${value}T12:00:00`).getTime();
  const lower = new Date(createdAt).getTime();
  const upper = Date.now();
  return new Date(Math.min(Math.max(noon, lower), upper)).toISOString();
}
