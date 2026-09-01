import { NavLink } from "react-router-dom";
import "./layout.css";

const LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/analyze", label: "Analyze Claim" },
  { to: "/dashboard", label: "Dashboard" },
  { to: "/map", label: "Map" },
  { to: "/claims", label: "Claims" },
  { to: "/alerts", label: "Alerts" },
];

export function NavBar() {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <NavLink to="/" className="navbar-brand">
          <span className="navbar-brand-mark" aria-hidden="true">HMT</span>
          <span className="navbar-brand-text">Hyperlocal Misinformation Tracker</span>
        </NavLink>
        <nav className="navbar-links" aria-label="Main navigation">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => `navbar-link${isActive ? " navbar-link-active" : ""}`}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
