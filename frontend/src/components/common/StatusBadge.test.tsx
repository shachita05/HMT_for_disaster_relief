import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders TRUE with the good/success styling", () => {
    render(<StatusBadge verdict="TRUE" />);
    const badge = screen.getByText("TRUE");
    expect(badge).toBeInTheDocument();
    expect(badge.closest(".badge")).toHaveClass("badge-good");
  });

  it("renders FAKE with the critical styling", () => {
    render(<StatusBadge verdict="FAKE" />);
    const badge = screen.getByText("FAKE");
    expect(badge.closest(".badge")).toHaveClass("badge-critical");
  });

  it("renders UNVERIFIED with the warning styling, distinct from TRUE/FAKE", () => {
    render(<StatusBadge verdict="UNVERIFIED" />);
    const badge = screen.getByText("UNVERIFIED");
    expect(badge.closest(".badge")).toHaveClass("badge-warning");
  });

  it("renders DISPUTED with its own styling, distinct from UNVERIFIED/FAKE", () => {
    render(<StatusBadge verdict="DISPUTED" />);
    const badge = screen.getByText("DISPUTED");
    expect(badge.closest(".badge")).toHaveClass("badge-serious");
  });
});
