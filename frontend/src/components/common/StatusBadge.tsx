import type { OverallVerdict } from "../../types";
import "./badges.css";

const VERDICT_META: Record<OverallVerdict, { label: string; icon: string; className: string }> = {
  TRUE: { label: "TRUE", icon: "✓", className: "badge-good" },
  FAKE: { label: "FAKE", icon: "✕", className: "badge-critical" },
  UNVERIFIED: { label: "UNVERIFIED", icon: "?", className: "badge-warning" },
  // Fact-checker debunked specific content while independent evidence
  // separately confirms the underlying event -- distinct from both a
  // confident FAKE and a plain "we don't know" UNVERIFIED.
  DISPUTED: { label: "DISPUTED", icon: "⚠", className: "badge-serious" },
};

export function StatusBadge({ verdict }: { verdict: OverallVerdict }) {
  const meta = VERDICT_META[verdict];
  return (
    <span className={`badge ${meta.className}`}>
      <span aria-hidden="true">{meta.icon}</span>
      {meta.label}
    </span>
  );
}
