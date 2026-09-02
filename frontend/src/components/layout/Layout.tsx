import type { ReactNode } from "react";
import { NavBar } from "./NavBar";
import { BottomNav } from "./BottomNav";
import "./layout.css";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100%" }}>
      <NavBar />
      <main style={{ flex: 1 }}>{children}</main>
      <footer className="footer">
        <p className="footer-note">
          HMT is a disaster information analysis and misinformation tracking system that checks each claim live
          against fact-checkers, news, and social media -- a BE capstone project, not an emergency-response system.
        </p>
      </footer>
      <BottomNav />
    </div>
  );
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: ReactNode }) {
  return (
    <div className="page-header">
      <h1 className="page-title">{title}</h1>
      {subtitle && <p className="page-subtitle">{subtitle}</p>}
    </div>
  );
}
