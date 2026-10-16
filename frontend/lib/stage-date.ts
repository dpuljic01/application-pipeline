// Helpers for picking a stage date with <input type="date"> (YYYY-MM-DD, in
// the user's local timezone) and turning it into the ISO datetime the API
// validates against (it must not be in the future).

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

// Noon avoids the date rolling over across timezones, but picking today
// before noon would then be "in the future" - clamp to now.
export function fromDateInputValue(value: string): string {
  const noon = new Date(`${value}T12:00:00`).getTime();
  return new Date(Math.min(noon, Date.now())).toISOString();
}
