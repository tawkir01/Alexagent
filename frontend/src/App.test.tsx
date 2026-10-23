import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import App from "./App";

afterEach(() => {
  cleanup();
  window.history.replaceState({}, "", "/");
  vi.unstubAllGlobals();
});

describe("CampusFlow sign in", () => {
  it("shows the sign-in form when there is no authenticated session", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ authenticated: false }),
    }));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><BrowserRouter><App /></BrowserRouter></QueryClientProvider>);
    expect(await screen.findByRole("heading", { name: /make room for/i })).toBeInTheDocument();
    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("carries source evidence through the radar, twin simulation, and pending plan review", async () => {
    window.history.replaceState({}, "", "/radar");
    let noticePublished = false;
    let simulationBody: Record<string, unknown> | undefined;
    let proposalBody: Record<string, unknown> | undefined;
    const source = {
      source_id: "LMS-CS315-210", title: "DBMS LMS assignment", type: "lms",
      content: "Lab deadline: October 28.", published_at: "2026-10-22T09:00:00+05:30", verified: true,
    };
    const assignment = {
      id: 2, title: "Normalization & SQL lab", description: "Submit the report.",
      due_at: "2026-10-28T23:59:00+05:30", status: "upcoming", estimated_hours: 3, importance: null,
      course: { code: "CS315", name: "Database Management Systems", color: "blue" },
      updated_at: "2026-10-22T09:00:00+05:30",
    };
    const dashboard = {
      student: { name: "Student", program: "Computer Engineering" },
      stats: { courses: 1, upcoming: 1, changes: 0, conflicts: 0 },
      courses: [assignment.course], assignments: [assignment], changes: [], conflicts: [],
      notices: [source], integrations: {},
    };
    const radar = {
      history: [{
        id: 1, entity_type: "assignment", entity_id: "2", assignment_id: 2,
        assignment: "Normalization & SQL lab", field: "due_at",
        old_value: "2026-10-28T23:59:00+05:30", new_value: "2026-10-30T23:59:00+05:30",
        source_id: "NOTICE-CS315-18", detected_at: "2026-10-23T09:00:00+05:30",
        status: "disputed", evidence_ids: ["LMS-CS315-210", "NOTICE-CS315-18"],
      }],
      conflicts: [], sources: [
        source,
        { ...source, source_id: "NOTICE-CS315-18", title: "Updated DBMS lab schedule", type: "notice", content: "Lab deadline: October 30." },
      ],
      demo_notice_published: noticePublished,
    };
    const preferences = {
      availability: { "2026-10-23": 3, "2026-10-24": 4, "2026-10-25": 4 },
      session_minutes: 60, importance: {},
      planned_sessions: [{ id: "existing-session", assignment_id: 2, date: "2026-10-23", minutes: 60 }],
    };
    const simulation = {
      scenario: { lost_hours_tomorrow: 2 }, schedule: [], risks: [{
        assignment_id: 2, assignment: assignment.title, course: "CS315", due_at: assignment.due_at,
        planning_due: "2026-10-28", days_remaining: 5, estimated_hours_remaining: 3,
        available_hours_before_due: 10, workload_score: 11, uncertainty_points: 12,
        priority_score: 23, status: "Needs attention", importance: null,
        deadline_uncertainty: { status: "disputed", window_start: "2026-10-28", window_end: "2026-10-30", source_ids: ["LMS-CS315-210", "NOTICE-CS315-18"], explanation: "Dates disagree across current sources." },
        explanation: "Workload is manageable but deadline details are disputed.",
      }],
      unscheduled: [], summary: { task_count: 1, remaining_work_hours: 3, available_capacity_hours: 9, fits: true },
      assumptions: ["The scenario removes 2 available hours."], alternatives: ["Use a shorter session."],
      planned_sessions: preferences.planned_sessions, preferences,
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/session") return { ok: true, json: async () => ({ authenticated: true, username: "Student" }) };
      if (path === "/api/dashboard") return { ok: true, json: async () => dashboard };
      if (path === "/api/radar") return { ok: true, json: async () => ({ ...radar, demo_notice_published: noticePublished }) };
      if (path === "/api/demo/publish-notice") {
        noticePublished = true;
        return { ok: true, json: async () => ({ created: true }) };
      }
      if (path === "/api/twin/preferences") return { ok: true, json: async () => preferences };
      if (path === "/api/twin/simulate") {
        simulationBody = JSON.parse(String(init?.body));
        return { ok: true, json: async () => simulation };
      }
      if (path === "/api/twin/proposals") {
        proposalBody = JSON.parse(String(init?.body));
        return { ok: true, json: async () => ({ id: 1, status: "pending", payload: { outcome: "pending_student_review" } }) };
      }
      throw new Error(`Unexpected API request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const user = userEvent.setup();
    render(<QueryClientProvider client={queryClient}><BrowserRouter><App /></BrowserRouter></QueryClientProvider>);

    expect(await screen.findByRole("heading", { name: "What changed, and why" })).toBeInTheDocument();
    await user.click(await screen.findByText("LMS-CS315-210 · DBMS LMS assignment"));
    expect(screen.getByText("Lab deadline: October 28.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Publish Oct 30 notice" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Notice detected" })).toBeDisabled());

    await user.click(screen.getByRole("link", { name: "Digital Twin" }));
    expect(await screen.findByRole("heading", { name: "Try a different week" })).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Simulate changes" }));
    expect(await screen.findByText("Workload is manageable but deadline details are disputed.")).toBeInTheDocument();
    expect(simulationBody).toMatchObject({ lost_hours_tomorrow: 2 });
    await user.click(screen.getByRole("button", { name: "Review revised plan" }));
    expect(await screen.findByText(/Proposal saved as pending review/)).toBeInTheDocument();
    expect(proposalBody).toMatchObject({ lost_hours_tomorrow: 2 });
  });
});
