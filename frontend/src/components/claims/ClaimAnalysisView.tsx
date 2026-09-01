import type { ClaimDetail } from "../../types";
import { StatusBadge } from "../common/StatusBadge";
import { PriorityBadge } from "../common/PriorityBadge";
import { ReliabilityMeter } from "../common/ReliabilityMeter";

// Shared by AnalyzeClaim (right after submission) and ClaimDetails (for any
// previously-persisted claim, live or historical) so the full-analysis
// layout is defined once.
export function ClaimAnalysisView({ result }: { result: ClaimDetail }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="card">
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
          <StatusBadge verdict={result.overall_verdict} />
          <PriorityBadge level={result.priority} />
        </div>
        <p style={{ margin: "0 0 6px", fontSize: 16, fontWeight: 600 }}>{result.official_verification_message}</p>
        <p className="muted" style={{ margin: "0 0 10px", fontSize: 13 }}>
          Model's own prediction: {result.classification} ({result.disaster_type} ·{" "}
          {(result.confidence * 100).toFixed(0)}% confidence) — {result.reason}
        </p>
        <ReliabilityMeter score={result.reliability_score} band={result.reliability_band} />
      </div>

      <div className="grid grid-cols-2">
        <div className="card">
          <p className="card-title">Location</p>
          {result.locations.length === 0 && <p className="muted">No location resolved.</p>}
          {result.locations.map((loc) => (
            <div key={loc.id} style={{ marginBottom: 8, fontSize: 14 }}>
              <strong>{[loc.locality, loc.city, loc.district, loc.state].filter(Boolean).join(", ")}</strong>
              {loc.is_primary && <span className="muted"> (primary)</span>}
              <div className="muted" style={{ fontSize: 12 }}>
                {loc.match_level} match ({loc.match_type})
                {loc.pin_code && ` · PIN ${loc.pin_code}`}
                {loc.coordinate_precision && loc.coordinate_precision !== "none" && ` · plotted at ${loc.coordinate_precision}-level centroid`}
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <p className="card-title">Priority reasoning</p>
          {result.priority_reasons.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14 }}>
              {result.priority_reasons.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          ) : (
            <p className="muted">No specific priority factors recorded.</p>
          )}
          {result.top_terms.length > 0 && (
            <>
              <p className="card-title" style={{ marginTop: 16 }}>Why the model said this</p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {result.top_terms.slice(0, 6).map(([term, weight]) => (
                  <span
                    key={term}
                    className="badge"
                    style={{
                      background: weight >= 0 ? "color-mix(in srgb, var(--status-good) 14%, transparent)" : "color-mix(in srgb, var(--status-critical) 14%, transparent)",
                      color: weight >= 0 ? "var(--status-good)" : "var(--status-critical)",
                    }}
                  >
                    {term} ({weight >= 0 ? "+" : ""}{weight.toFixed(2)})
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Evidence is a deliberately SEPARATE panel from the ML verdict above --
          it is independently-sourced support/contradiction, not proof produced
          by the classifier. Never merge these visually. */}
      <div className="card">
        <p className="card-title">Evidence (independent of the ML verdict)</p>
        {result.evidence.length === 0 ? (
          <p className="muted">
            No supporting evidence found in the stored corpus or recent live feeds. This does not mean the claim
            is false — only that no matching record was found.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {result.evidence.map((ev) => (
              <div key={ev.id} style={{ borderLeft: "3px solid var(--series-1)", paddingLeft: 10 }}>
                <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>
                  {ev.source}
                  {ev.url && (
                    <a href={ev.url} target="_blank" rel="noreferrer" style={{ marginLeft: 8, fontWeight: 400 }}>
                      source ↗
                    </a>
                  )}
                </p>
                <p className="muted" style={{ margin: "2px 0 0", fontSize: 13 }}>{ev.description}</p>
              </div>
            ))}
          </div>
        )}
        <p className="muted" style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}>
          Verification status: {result.verification_status === "matched" ? "matched against stored IFND corpus" : "no stored-corpus match"} — checked
          against a stored dataset and periodic public feeds (USGS, GDACS), not live NDMA/IMD/PIB integration.
        </p>
      </div>
    </div>
  );
}
