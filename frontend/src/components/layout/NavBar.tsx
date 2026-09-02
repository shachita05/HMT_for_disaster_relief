import { NavLink } from "react-router-dom";
import { NAV_LINKS } from "./navLinks";
import "./layout.css";

export function NavBar() {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <NavLink to="/" className="navbar-brand">
          <span className="navbar-brand-mark material-symbols-outlined" aria-hidden="true">hub</span>
          <span className="navbar-brand-text">HMT Hyperlocal Misinformation Tracker</span>
        </NavLink>
        <nav className="navbar-links" aria-label="Main navigation">
          {NAV_LINKS.map((link) => (
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
