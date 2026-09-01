import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { Home } from "./pages/Home";
import { AnalyzeClaim } from "./pages/AnalyzeClaim";
import { Dashboard } from "./pages/Dashboard";
import { Claims } from "./pages/Claims";
import { ClaimDetails } from "./pages/ClaimDetails";
import { Alerts } from "./pages/Alerts";
import { LoadingSpinner } from "./components/common/LoadingSpinner";

// Lazy-loaded: Leaflet is the single heaviest dependency in the bundle
// and only the Map page needs it -- no reason to ship it on every route.
const MapPage = lazy(() => import("./pages/Map").then((m) => ({ default: m.MapPage })));

export function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/analyze" element={<AnalyzeClaim />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route
          path="/map"
          element={
            <Suspense fallback={<div className="page"><LoadingSpinner label="Loading map…" /></div>}>
              <MapPage />
            </Suspense>
          }
        />
        <Route path="/claims" element={<Claims />} />
        <Route path="/claims/:id" element={<ClaimDetails />} />
        <Route path="/alerts" element={<Alerts />} />
      </Routes>
    </Layout>
  );
}
