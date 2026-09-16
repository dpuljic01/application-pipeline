import { postingScoreColor } from "@/lib/jd-score";

const SIZE = 96;
const STROKE = 8;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function PostingScoreGauge({ score, label }: { score: number; label: string }) {
  const color = postingScoreColor(score);
  const offset = CIRCUMFERENCE * (1 - score / 100);

  return (
    <div className="flex items-center gap-4">
      <svg
        width={SIZE}
        height={SIZE}
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="-rotate-90"
        role="img"
        aria-label={`${label}: ${score} out of 100`}
      >
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke="var(--border)"
          strokeWidth={STROKE}
        />
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.4s ease" }}
        />
        <text
          x={SIZE / 2}
          y={SIZE / 2}
          transform={`rotate(90 ${SIZE / 2} ${SIZE / 2})`}
          textAnchor="middle"
          dominantBaseline="central"
          className="font-mono text-2xl font-medium tabular-nums"
          fill="var(--foreground)"
        >
          {score}
        </text>
      </svg>
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">Based on red flags,</p>
        <p className="text-xs text-muted-foreground">missing info, and salary clarity</p>
      </div>
    </div>
  );
}
