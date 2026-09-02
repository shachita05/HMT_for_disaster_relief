import { Link } from "react-router-dom";
import { PageHeader } from "../components/layout/Layout";

export function Home() {
  return (
    <div className="page">
      <PageHeader
        title="Hyperlocal Misinformation Tracker for Disaster Relief"
        subtitle="An intelligent platform for analyzing, verifying, and tracking disaster-related information to support reliable and timely relief decisions."
      />

      <div className="card" style={{ marginBottom: 24 }}>
        <p style={{ marginTop: 0 }}>
          During disasters, critical information spreads rapidly across online platforms, making it difficult to
          distinguish genuine reports from misinformation. HMT analyzes disaster-related claims using NLP and
          machine learning to identify the disaster type, extract the affected location, assess misinformation
          risk, and evaluate supporting evidence. The system generates reliability and priority scores to help
          relief organizations identify credible information and focus their response efforts.
        </p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link to="/analyze" className="btn btn-primary">Analyze a claim</Link>
          <Link to="/dashboard" className="btn">View dashboard</Link>
        </div>
      </div>

      <div className="grid grid-cols-3">
        <Feature
          title="Beyond Binary Classification"
          body="HMT classifies disaster-related claims as TRUE, FAKE, or UNVERIFIED, while providing confidence scores to indicate the certainty of each prediction."
        />
        <Feature
          title="Evidence-Based Verification"
          body="Model predictions are presented separately from independently sourced evidence, including trusted news, fact-checking sources, and disaster information feeds."
        />
        <Feature
          title="Actionable Disaster Intelligence"
          body="Each analyzed claim is enriched with location, disaster type, reliability, and priority information to help identify reports that may require further verification or relief attention."
        />
      </div>
    </div>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <div className="card">
      <p style={{ fontWeight: 600, margin: "0 0 6px" }}>{title}</p>
      <p className="muted" style={{ margin: 0, fontSize: 14, lineHeight: 1.5 }}>{body}</p>
    </div>
  );
}
