import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import type { MapPoint } from "../../types";
import { StatusBadge } from "../common/StatusBadge";
import { PriorityBadge } from "../common/PriorityBadge";

// CircleMarker instead of Leaflet's default pin Marker deliberately --
// the default marker's icon image paths break under Vite's bundling
// (a well-known Leaflet+bundler issue) and a colored circle also lets us
// encode priority directly without a sprite-sheet of colored pins.
const PRIORITY_COLOR: Record<string, string> = {
  HIGH: "#ef4444",
  MEDIUM: "#ffb100",
  LOW: "#10b981",
};

const INDIA_CENTER: [number, number] = [22.5, 80];

export function ClaimsMap({ points }: { points: MapPoint[] }) {
  return (
    <MapContainer center={INDIA_CENTER} zoom={5} style={{ height: 520, width: "100%", borderRadius: 12 }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {points.map((p) => (
        <CircleMarker
          key={p.claim_id}
          center={[p.latitude, p.longitude]}
          radius={7}
          pathOptions={{
            color: "#fff",
            weight: 1.5,
            fillColor: PRIORITY_COLOR[p.priority] ?? "#8c909f",
            fillOpacity: 0.85,
          }}
        >
          <Popup>
            <div style={{ minWidth: 180 }}>
              <div style={{ display: "flex", gap: 6, marginBottom: 6, flexWrap: "wrap" }}>
                <StatusBadge verdict={p.classification} />
                <PriorityBadge level={p.priority} />
              </div>
              <p style={{ margin: "4px 0", fontWeight: 600 }}>{p.disaster_type}</p>
              <p style={{ margin: "2px 0", fontSize: 13 }}>{p.matched_text}</p>
              <p style={{ margin: "2px 0", fontSize: 12, color: "#666" }}>
                {new Date(p.submitted_at).toLocaleDateString()} &middot; {p.coordinate_precision}-level location
                {p.is_historical_seed ? " · historical dataset record" : ""}
              </p>
              <a href={`/claims/${p.claim_id}`} style={{ fontSize: 12 }}>
                View claim details →
              </a>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
