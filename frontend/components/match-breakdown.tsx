import type { MatchComponentScore, MatchDetails } from "@/lib/types";

const COMPONENT_LABELS: [key: string, label: string][] = [
  ["skills", "Skills"],
  ["seniority", "Seniority"],
  ["language", "Languages"],
  ["salary", "Salary"],
  ["remote_policy", "Remote policy"],
];

interface LanguageResult {
  language: string;
  required_level: string | null;
  your_level: string | null;
  credit: number;
}

function detailFor(key: string, component: MatchComponentScore): string | null {
  if (key === "skills") {
    const ratio = component.required_ratio;
    const missingCore = (component.core_skills as string[] | undefined)?.filter(
      (s) => !(component.matched_core as string[] | undefined)?.includes(s),
    );
    const parts: string[] = [];
    if (typeof ratio === "number") parts.push(`${Math.round(ratio * 100)}% of required`);
    if (missingCore?.length) parts.push(`missing core: ${missingCore.join(", ")}`);
    return parts.join(" · ") || null;
  }
  if (key === "language") {
    const requirements = component.requirements as LanguageResult[] | undefined;
    const short = requirements?.filter((r) => r.credit < 1) ?? [];
    return (
      short
        .map((r) =>
          r.your_level === "missing"
            ? `${r.language} missing`
            : `${r.language}: needs ${r.required_level}, you ${r.your_level}`,
        )
        .join(" · ") || null
    );
  }
  return null;
}

// Rule-based half of the match: per-component points, plus the reasons the
// total is lower than their sum. Older scores have no adjustments field.
export function MatchBreakdown({ details }: { details: MatchDetails }) {
  const adjustments = details.adjustments ?? [];
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium text-muted-foreground">Score breakdown</p>
      <dl className="space-y-1">
        {COMPONENT_LABELS.map(([key, label]) => {
          const component = details.components[key];
          if (!component) return null;
          const detail = detailFor(key, component);
          return (
            <div key={key} className="flex items-baseline justify-between gap-3 text-sm">
              <dt className="min-w-0 text-foreground">
                {label}
                {detail && (
                  <span className="ml-2 text-xs text-muted-foreground">{detail}</span>
                )}
              </dt>
              <dd className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                {component.score}/{component.max}
              </dd>
            </div>
          );
        })}
      </dl>
      {adjustments.length > 0 && (
        <ul className="mt-2 space-y-1 rounded-[3px] border border-[var(--primary)]/40 bg-[var(--primary)]/10 px-3 py-2 text-xs text-[var(--primary)]">
          {adjustments.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
