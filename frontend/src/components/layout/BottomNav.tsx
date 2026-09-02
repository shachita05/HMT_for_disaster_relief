import { NavLink } from "react-router-dom";
import { NAV_LINKS } from "./navLinks";
import "./layout.css";

// Mobile-only (see .bottom-nav's max-width:760px media query) -- the
// desktop horizontal nav strip hides at the same breakpoint, so exactly
// one navigation surface is ever visible.
export function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="Main navigation">
      {NAV_LINKS.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          end={link.end}
          className={({ isActive }) => `bottom-nav-link${isActive ? " bottom-nav-link-active" : ""}`}
        >
          <span className="material-symbols-outlined bottom-nav-icon" aria-hidden="true">{link.icon}</span>
          {link.label}
        </NavLink>
      ))}
    </nav>
  );
}
