import { PageHeader } from "../components/layout/Layout";
import { useStatsOverview, useDisasterTypeStats, useTopLocations, useTimeline } from "../hooks/useStats";
import { useClaims } from "../hooks/useClaims";
import { useAlerts } from "../hooks/useAlerts";
import { useFeedStatus } from "../hooks/useFeedStatus";
import { VerdictDonutChart } from "../components/charts/VerdictDonutChart";
import { DisasterTypeBarChart } from "../components/charts/DisasterTypeBarChart";
import { TopLocationsBarChart } from "../components/charts/TopLocationsBarChart";
import { ClaimsTimelineChart } from "../components/charts/ClaimsTimelineChart";
import { ClaimTable } from "../components/claims/ClaimTable";
import { AlertList } from "../components/alerts/AlertList";
import { useAcknowledgeAlert } from "../hooks/useAlerts";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorState } from "../components/common/ErrorState";
import type { FeedHealth } from "../types";

export function Dashboard() {
  const overview = useStatsOverview();
  const disasterTypes = useDisasterTypeStats();
  const locations = useTopLocations("state", 8);
  const timeline = useTimeline();
  const recentClaims = useClaims({ limit: 8 });
  const alerts = useAlerts({ acknowledged: false });
  const feedStatus = useFeedStatus();
  const acknowledge = useAcknowledgeAlert();

  if (overview.isLoading) return <div className="page"><LoadingSpinner label="Loading dashboard…" /></div>;
  if (overview.isError || !overview.data) {
    return <div className="page"><ErrorState message="Could not load dashboard statistics." onRetry={() => overview.refetch()} /></div>;
  }

  const s = overview.data;

  return (
    <div className="page">
      <PageHeader title="Dashboard" subtitle="Aggregate statistics over all analyzed claims, both live-submitted and the seeded historical dataset." />

      <div className="grid grid-cols-4" style={{ marginBottom: 20 }}>
        <StatTile label="Total claims analyzed" value={s.total_claims} />
        <StatTile label="High priority" value={s.high_priority_count} />
        <StatTile label="Verified against corpus" value={`${(s.verification_rate * 100).toFixed(0)}%`} />
        <StatTile label="Open alerts" value={alerts.data?.total ?? "—"} />
      </div>

      {feedStatus.data && <FeedStatusStrip feeds={feedStatus.data} />}

      <div className="grid grid-cols-2" style={{ marginTop: 20, marginBottom: 20 }}>
        <div className="card">
          <p className="card-title">Verdict breakdown</p>
          <VerdictDonutChart trueCount={s.true_count} fakeCount={s.fake_count} unverifiedCount={s.unverified_count} />
        </div>
        <div className="card">
          <p className="card-title">Claims over time</p>
          {timeline.data ? <ClaimsTimelineChart data={timeline.data} /> : <LoadingSpinner />}
        </div>
        <div className="card">
          <p className="card-title">Disaster types</p>
          {disasterTypes.data ? <DisasterTypeBarChart data={disasterTypes.data} /> : <LoadingSpinner />}
        </div>
        <div className="card">
          <p className="card-title">Top affected states</p>
          {locations.data ? <TopLocationsBarChart data={locations.data} /> : <LoadingSpinner />}
        </div>
      </div>

      <div className="grid grid-cols-2" style={{ alignItems: "start" }}>
        <div className="card">
          <p className="card-title">Recent claims</p>
          {recentClaims.data ? <ClaimTable claims={recentClaims.data.items} /> : <LoadingSpinner />}
        </div>
        <div>
          <p className="card-title" style={{ marginBottom: 12 }}>Open high-priority alerts</p>
          {alerts.data && (
            <AlertList
              alerts={alerts.data.items.slice(0, 5)}
              onAcknowledge={(id) => acknowledge.mutate(id)}
              acknowledgingId={acknowledge.isPending ? (acknowledge.variables ?? null) : null}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card">
      <p style={{ margin: "0 0 6px", fontSize: 12, color: "var(--text-muted)" }}>{label}</p>
      <p style={{ margin: 0, fontSize: "1.6rem", fontWeight: 700 }}>{value}</p>
    </div>
  );
}

function FeedStatusStrip({ feeds }: { feeds: FeedHealth[] }) {
  const dotColor: Record<FeedHealth["status"], string> = {
    ok: "var(--status-good)",
    error: "var(--status-critical)",
    not_configured: "var(--text-muted)",
    unknown: "var(--text-muted)",
  };
  return (
    <div className="card" style={{ display: "flex", gap: 18, flexWrap: "wrap", alignItems: "center", fontSize: 13 }}>
      <span className="muted" style={{ fontSize: 12 }}>Live feed status (background sources refresh every 15 min; each claim also runs live checks):</span>
      {feeds.map((f) => (
        <span key={f.name} style={{ display: "flex", alignItems: "center", gap: 6 }} title={f.last_error ?? undefined}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: dotColor[f.status], display: "inline-block" }} />
          {f.name}
        </span>
      ))}
    </div>
  );
}
