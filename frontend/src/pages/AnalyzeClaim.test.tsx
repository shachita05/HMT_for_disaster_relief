import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AnalyzeClaim } from "./AnalyzeClaim";
import { ApiError } from "../api/client";
import type { ClaimDetail } from "../types";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return { ...actual, api: { ...actual.api, analyzeClaim: vi.fn() } };
});

import { api } from "../api/client";

const SAMPLE_RESULT: ClaimDetail = {
  id: 1,
  text: "Heavy rainfall has caused severe flooding in Whitefield, Bengaluru.",
  source: "manual",
  source_url: null,
  submitted_at: "2026-08-29T10:00:00Z",
  disaster_type: "Flood",
  classification: "TRUE",
  confidence: 0.78,
  reliability_score: 54,
  reliability_band: "MEDIUM",
  priority: "MEDIUM",
  priority_score: 4,
  verification_status: "not_matched",
  is_historical_seed: false,
  all_disaster_types: ["Flood"],
  top_terms: [["heavy", 0.28], ["rainfall", 0.14]],
  priority_reasons: ["disaster type 'Flood' (+2)"],
  reliability_reasons: ["ML classification confidence contributes 27/35"],
  reason: "The claim matches 'Flood'-type disaster keywords.",
  locations: [],
  evidence: [],
  official_verification_message: "Partially supported -- classified TRUE by the model, but independent official confirmation is limited.",
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AnalyzeClaim />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("AnalyzeClaim page", () => {
  beforeEach(() => {
    vi.mocked(api.analyzeClaim).mockReset();
  });

  it("shows the analysis result after a successful submission", async () => {
    vi.mocked(api.analyzeClaim).mockResolvedValue(SAMPLE_RESULT);
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByPlaceholderText(/heavy rainfall/i), "Heavy rainfall has caused flooding");
    await user.click(screen.getByRole("button", { name: /^analyze$/i }));

    await waitFor(() => expect(screen.getByText(/Flood.*model confidence/i)).toBeInTheDocument());
    expect(screen.getByText("TRUE")).toBeInTheDocument();
  });

  it("shows an error state when the API call fails", async () => {
    vi.mocked(api.analyzeClaim).mockRejectedValue(new ApiError("Could not reach the HMT API. Is the backend running?", 0));
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByPlaceholderText(/heavy rainfall/i), "Heavy rainfall has caused flooding");
    await user.click(screen.getByRole("button", { name: /^analyze$/i }));

    await waitFor(() => expect(screen.getByText(/could not reach the hmt api/i)).toBeInTheDocument());
  });
});
