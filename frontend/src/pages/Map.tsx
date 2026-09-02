import { useState } from "react";
import { PageHeader } from "../components/layout/Layout";
import { useMapClaims } from "../hooks/useMap";
import { ClaimsMap } from "../components/map/ClaimsMap";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ErrorState } from "../components/common/ErrorState";

const DISASTER_TYPES = [
  "Flood", "Cyclone", "Earthquake", "Landslide", "Heavy Rain", "Cloudburst",
  "Drought", "Wildfire", "Tsunami", "Avalanche", "Storm", "Rescue/Evacuation", "Other",
];

export function MapPage() {
  const [disasterType, setDisasterType] = useState("");
  const [priority, setPriority] = useState("");
  const { data, isLoading, isError, refetch } = useMapClaims({
    disaster_type: disasterType || undefined,
    priority: priority || undefined,
  });

  return (
    <div className="page">
      <PageHeader
        title="Map"
        subtitle="Locations of analyzed disaster-related claims — this represents analyzed information, not physical sensor data. Locality-level claims are plotted at their city's centroid, not a street-level point."
      />

      <div className="card" style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <select className="input" style={{ maxWidth: 200 }} value={disasterType} onChange={(e) => setDisasterType(e.target.value)}>
          <option value="">All disaster types</option>
          {DISASTER_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select className="input" style={{ maxWidth: 160 }} value={priority} onChange={(e) => setPriority(e.target.value)}>
          <option value="">All priorities</option>
          <option value="HIGH">High priority</option>
          <option value="MEDIUM">Medium priority</option>
          <option value="LOW">Low priority</option>
        </select>
        <div style={{ marginLeft: "auto", display: "flex", gap: 14, fontSize: 13, alignItems: "center" }}>
          <Legend color="#ef4444" label="High" />
          <Legend color="#ffb100" label="Medium" />
          <Legend color="#10b981" label="Low" />
        </div>
      </div>

      {isLoading && <LoadingSpinner label="Loading map points…" />}
      {isError && <ErrorState message="Could not load map data." onRetry={() => refetch()} />}
      {data && <ClaimsMap points={data} />}
      {data && <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>{data.length} claims plotted.</p>}
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
      <span style={{ width: 9, height: 9, borderRadius: "50%", background: color, display: "inline-block" }} />
      {label}
    </span>
  );
}
