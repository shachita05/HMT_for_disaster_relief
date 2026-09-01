import { Link } from "react-router-dom";
import { PageHeader } from "../components/layout/Layout";

export function Home() {
  return (
    <div className="page">
      <PageHeader
        title="Hyperlocal Misinformation Tracker for Disaster Relief"
        subtitle="A disaster information analysis and misinformation tracking system — built for a BE capstone project."
      />

      <div className="card" style={{ marginBottom: 24 }}>
        <p style={{ marginTop: 0 }}>
          During disasters, large volumes of information circulate online — some genuine, some outdated,
          exaggerated, or entirely false. Misinformation can misdirect relief resources, cause panic, and delay
          genuine response efforts. HMT analyzes disaster-related text and produces a disaster type, a resolved
          location, a misinformation classification, evidence, a reliability score, and a priority level — so
          relief organizations can triage information rather than treat every report as equally trustworthy.
        </p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link to="/analyze" className="btn btn-primary">Analyze a claim</Link>
          <Link to="/dashboard" className="btn">View dashboard</Link>
        </div>
      </div>

      <div className="grid grid-cols-3">
        <Feature
          title="Not merely TRUE/FALSE"
          body="Claims are classified TRUE, FAKE, or UNVERIFIED — the model does not force a binary call when its own confidence is low."
        />
        <Feature
          title="Evidence, kept separate"
          body="Model predictions and independently-sourced evidence (fact-checkers, news, social media, disaster feeds) are always shown as distinct, never merged."
        />
        <Feature
          title="Honest about scope"
          body="Every claim is checked live against real fact-checking, news, and social media sources — this is a research prototype, not a replacement for official emergency services."
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
