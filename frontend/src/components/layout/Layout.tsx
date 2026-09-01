import type { ReactNode } from "react";
import { NavBar } from "./NavBar";
import "./layout.css";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <NavBar />
      <main>{children}</main>
      <p className="footer-note">
        HMT is a disaster information analysis and misinformation tracking system that checks each claim live
        against fact-checkers, news, and social media -- a BE capstone project, not an emergency-response system.
      </p>
    </>
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
