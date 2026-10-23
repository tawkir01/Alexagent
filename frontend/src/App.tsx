import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Bell, BookOpen, CalendarDays,
  Check, CheckCircle2, ChevronRight, CircleAlert, Clock3, Command, FileText, GraduationCap,
  History, LogOut, Menu, MessageCircle, Plus, Search, Send, ShieldCheck, SlidersHorizontal,
  Sparkles, X,
} from "lucide-react";

type Source = {
  source_id: string; title: string; type: string; content: string; published_at: string; verified: boolean;
  record_key?: string | null; record_kind?: string | null; record_value?: string | null;
};
type Assignment = {
  id: number; title: string; description: string; due_at: string; status: string; estimated_hours: number;
  course: { code: string; name: string; color: string }; updated_at: string;
};
type Conflict = {
  assignment_id: number; assignment: string; course: string; status: string; message: string;
  sources: { source_id: string; source_title: string; due_at: string; published_at: string }[];
};
type Dashboard = {
  student: { name: string; program: string };
  stats: { courses: number; upcoming: number; changes: number; conflicts: number };
  courses: { code: string; name: string; color: string }[];
  assignments: Assignment[];
  changes: { assignment: string; course: string | null; field: string; status: string; old_due_at: string; new_due_at: string; source_id: string }[];
  conflicts: Conflict[];
  notices: Source[];
  integrations: Record<string, string>;
};
type RadarEvent = {
  id: number; entity_type: string; entity_id: string; assignment_id: number | null; assignment: string;
  field: string; old_value: string; new_value: string; source_id: string; detected_at: string;
  status: "verified" | "disputed" | "awaiting_confirmation"; evidence_ids: string[];
};
type RadarData = { history: RadarEvent[]; conflicts: Conflict[]; sources: Source[]; demo_notice_published: boolean };
type PlannedSession = { id: string; assignment_id: number; date: string; minutes: number };
type TwinPreferences = {
  availability: Record<string, number>; session_minutes: number; planned_sessions: PlannedSession[];
  importance: Record<string, number>;
};
type TwinScenario = {
  lost_hours_tomorrow: number;
  additional_assignment?: { title: string; due_date: string; estimated_hours: number; course_code?: string };
  increase_estimate?: { assignment_id: number; extra_hours: number };
  move_session?: { session_id: string; to_date: string };
};
type Risk = {
  assignment_id: number; assignment: string; course: string; due_at: string; planning_due: string;
  days_remaining: number; estimated_hours_remaining: number; available_hours_before_due: number;
  workload_score: number; uncertainty_points: number; priority_score: number; status: string;
  importance: number | null; deadline_uncertainty: { status: string; window_start?: string; window_end?: string; source_ids: string[]; explanation: string };
  explanation: string;
};
type TwinResult = {
  scenario: TwinScenario; schedule: { date: string; available_hours: number; sessions: { assignment_id: number; assignment: string; course: string; minutes: number; existing: boolean }[] }[];
  risks: Risk[]; unscheduled: { assignment_id: number; assignment: string; unscheduled_hours: number; due_at: string }[];
  summary: { task_count: number; remaining_work_hours: number; available_capacity_hours: number; fits: boolean };
  assumptions: string[]; alternatives: string[]; planned_sessions: PlannedSession[]; preferences: TwinPreferences;
};
type Answer = {
  answer: string; mode: string; verified_facts: { claim: string; source_ids: string[] }[];
  conflicts: Conflict[]; assumptions: string[]; recommendations: string[]; sources: Source[];
};
type Proposal = {
  id: number; kind: string; title: string; status: string;
  payload: {
    notice: string;
    sessions?: { day: number; assignment: string; course: string; due_at?: string; minutes: number; focus: string }[];
    schedule?: TwinResult["schedule"];
    risks?: Risk[];
    unscheduled?: TwinResult["unscheduled"];
    assumptions?: string[];
    alternatives?: string[];
    scenario?: TwinScenario;
    outcome?: string;
  };
};
type Audit = { id: number; actor: string; action: string; entity_type: string; entity_id: string; created_at: string };

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail ?? "We couldn’t complete that request.");
  return body as T;
}

function dateLabel(value: string, options: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" }) {
  return new Intl.DateTimeFormat("en-IN", options).format(new Date(value));
}
function dateTime(value: string) {
  return dateLabel(value, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
function changeValue(value: string, field: string) {
  if (["due_at", "deadline", "examination_date"].includes(field) && Number.isFinite(Date.parse(value))) {
    return dateTime(value);
  }
  return value;
}
function ErrorNotice({ error }: { error: Error | null }) {
  return error ? <div className="error-notice" role="alert"><CircleAlert size={16} />{error.message}</div> : null;
}
function Tag({ children, tone = "default" }: { children: ReactNode; tone?: string }) {
  return <span className={`tag tag-${tone}`}>{children}</span>;
}
function SectionTitle({ eyebrow, title, action }: { eyebrow: string; title: string; action?: ReactNode }) {
  return <div className="section-title"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1></div>{action}</div>;
}
function PageLoading() { return <div className="page-loading"><span className="spinner" /> Loading your workspace…</div>; }

function SignIn({ onSignedIn }: { onSignedIn: (name: string) => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true); setError("");
    try {
      const user = await api<{ username: string }>("/api/login", { method: "POST", body: JSON.stringify({ username: form.get("username"), password: form.get("password") }) });
      onSignedIn(user.username);
      navigate("/");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sign in failed.");
    } finally { setBusy(false); }
  }
  return <main className="signin-page">
    <section className="signin-card">
      <Brand />
      <p className="eyebrow">YOUR ACADEMIC COPILOT</p>
      <h1>Make room for<br /><span>what matters.</span></h1>
      <p className="signin-copy">A calmer way to keep up with classes, deadlines, and the details that change.</p>
      <form className="signin-form" onSubmit={submit}>
        <label htmlFor="username">Username</label><input id="username" name="username" autoComplete="username" required maxLength={80} />
        <label htmlFor="password">Password</label><input id="password" name="password" type="password" autoComplete="current-password" required maxLength={256} />
        <ErrorNotice error={error ? new Error(error) : null} />
        <button className="button button-primary" disabled={busy}>{busy ? "Signing in…" : <>Sign in <ArrowRight size={17} /></>}</button>
      </form>
      <div className="signin-private"><ShieldCheck size={15} /> Private demo workspace · synthetic data only</div>
    </section>
    <aside className="signin-visual">
      <div className="visual-orbit orbit-a" /><div className="visual-orbit orbit-b" />
      <div className="visual-card floating-one"><span className="visual-card-icon icon-lilac"><CalendarDays size={17} /></span><div><strong>One deadline moved</strong><small>Graph algorithms · Oct 25</small></div><ArrowUpRight size={16} /></div>
      <div className="visual-card floating-two"><span className="visual-card-icon icon-peach"><CircleAlert size={17} /></span><div><strong>Worth a second look</strong><small>Two sources disagree</small></div><span className="unread-dot" /></div>
      <div className="visual-center"><span className="visual-star"><Sparkles size={24} /></span><strong>Your semester,<br />a little more in sync.</strong></div>
      <p className="visual-caption">CONTEXT FOR THE NEXT THING</p>
    </aside>
  </main>;
}

function Brand() {
  return <Link to="/" className="brand"><span className="brand-icon"><Command size={18} strokeWidth={2.7} /></span><span>campus<span>flow</span></span></Link>;
}

function AppShell({ username, onLogout }: { username: string; onLogout: () => void }) {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const section = location.pathname === "/" ? "Overview" : location.pathname.slice(1).replace(/^\w/, (c) => c.toUpperCase());
  const nav = [
    { to: "/", label: "Overview", icon: Activity, end: true },
    { to: "/deadlines", label: "Deadlines", icon: CalendarDays },
    { to: "/radar", label: "Change Radar", icon: History },
    { to: "/twin", label: "Digital Twin", icon: SlidersHorizontal },
    { to: "/sources", label: "Notices & sources", icon: FileText },
    { to: "/study-plan", label: "Study plan", icon: BookOpen },
    { to: "/activity", label: "Activity log", icon: Clock3 },
  ];
  return <div className="app-shell">
    <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
      <Brand />
      <div className="workspace-label">STUDENT WORKSPACE</div>
      <nav className="side-nav" aria-label="Main navigation">
        {nav.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={() => setMenuOpen(false)} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}><Icon size={17} /><span>{label}</span>{label === "Deadlines" && <span className="nav-count">4</span>}</NavLink>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="demo-card"><span className="demo-pulse" /><div><strong>Demo data connected</strong><small>LMS sample workspace</small></div></div>
        <div className="profile-row"><span className="profile-avatar">{username.charAt(0).toUpperCase()}</span><div><strong>{username}</strong><small>Computer Engineering</small></div><button className="icon-button logout-button" onClick={onLogout} aria-label="Sign out" title="Sign out"><LogOut size={16} /></button></div>
      </div>
    </aside>
    {menuOpen && <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
    <main className="main-panel">
      <header className="topbar">
        <button className="icon-button mobile-menu" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle navigation">{menuOpen ? <X size={19} /> : <Menu size={19} />}</button>
        <div className="breadcrumb">Workspace <ChevronRight size={14} /><strong>{section}</strong></div>
        <div className="topbar-actions"><span className="today-label"><span className="status-dot" /> Demo mode</span><button className="icon-button notification-button" aria-label="Notifications"><Bell size={17} /><i /></button></div>
      </header>
      <div className="page-wrap">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/deadlines" element={<DeadlinesPage />} />
          <Route path="/radar" element={<ChangeRadarPage />} />
          <Route path="/twin" element={<DigitalTwinPage />} />
          <Route path="/sources" element={<SourcesPage />} />
          <Route path="/study-plan" element={<StudyPlanPage />} />
          <Route path="/activity" element={<ActivityPage />} />
          <Route path="*" element={<DashboardPage />} />
        </Routes>
        <footer className="page-footer"><span><Sparkles size={13} /> CampusFlow demo · Synthetic academic data</span><span>AI suggestions can be wrong — verify important dates with your instructor.</span></footer>
      </div>
    </main>
  </div>;
}

function useDashboard() {
  return useQuery({ queryKey: ["dashboard"], queryFn: () => api<Dashboard>("/api/dashboard") });
}

function DashboardPage() {
  const { data, isLoading, error } = useDashboard();
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const chat = useMutation({ mutationFn: (message: string) => api<Answer>("/api/chat", { method: "POST", body: JSON.stringify({ message }) }), onSuccess: setAnswer });
  if (isLoading) return <PageLoading />;
  if (!data) return <ErrorNotice error={error as Error | null} />;
  function ask(message = question) {
    if (message.trim()) { setQuestion(message); chat.mutate(message.trim()); }
  }
  const prompts = ["What changed this week?", "Which dates are conflicting?", "Help me make a study plan"];
  return <>
    <div className="welcome-row"><div><p className="eyebrow"><span className="sparkle-mini"><Sparkles size={13} /></span> FRIDAY, OCTOBER 23</p><h1>Good morning, {data.student.name.split(" ")[0]}<span className="accent-dot">.</span></h1><p className="welcome-sub">{data.student.program} <span>·</span> Let’s make sense of your week.</p></div><button className="button button-quiet" onClick={() => window.location.reload()}><Activity size={15} /> Refresh overview</button></div>
    <ErrorNotice error={error as Error | null} />
    <section className="stat-grid" aria-label="Academic overview">
      <StatCard icon={<GraduationCap size={17} />} label="Active courses" value={data.stats.courses} note="This semester" tone="mint" />
      <StatCard icon={<CalendarDays size={17} />} label="Upcoming deadlines" value={data.stats.upcoming} note="Next 14 days" tone="blue" />
      <StatCard icon={<ArrowDownRight size={17} />} label="Academic updates" value={data.stats.changes} note="Since your last check" tone="lilac" />
      <StatCard icon={<CircleAlert size={17} />} label="Need your attention" value={data.stats.conflicts} note="Conflicting sources" tone="peach" alert={data.stats.conflicts > 0} />
    </section>
    <div className="dashboard-grid">
      <section className="panel schedule-panel">
        <div className="panel-heading"><div><p className="eyebrow">COMING UP</p><h2>Your next deadlines</h2></div><Link className="text-link" to="/deadlines">All deadlines <ArrowRight size={14} /></Link></div>
        <div className="deadline-list">
          {data.assignments.slice(0, 4).map((item) => <DeadlineRow key={item.id} assignment={item} />)}
          {!data.assignments.length && <p className="empty-message">You’re all caught up.</p>}
        </div>
      </section>
      <section className="panel changes-panel">
        <div className="panel-heading"><div><p className="eyebrow">STAY IN THE LOOP</p><h2>Changes & conflicts</h2></div><span className="panel-icon"><Bell size={16} /></span></div>
        {data.changes.map((item) => <div className="change-item" key={`${item.source_id}-${item.field}`}><span className="change-icon"><ArrowDownRight size={16} /></span><div><strong>{item.assignment}</strong><p><s>{changeValue(item.old_due_at, item.field)}</s><ArrowRight size={12} /> <b>{changeValue(item.new_due_at, item.field)}</b>{item.course ? ` · ${item.course}` : ""}</p><small>{item.status.replaceAll("_", " ")} · {item.field.replaceAll("_", " ")} <span className="source-ref">{item.source_id}</span></small></div></div>)}
        {data.conflicts.map((item) => <ConflictCard key={item.assignment_id} conflict={item} compact />)}
      </section>
      <section className="panel assistant-panel">
        <div className="assistant-heading"><span className="assistant-spark"><Sparkles size={17} /></span><div><p className="eyebrow">CAMPUSFLOW ASSISTANT</p><h2>Ask about your academics</h2></div><Tag tone="green">Evidence-backed</Tag></div>
        <div className="prompt-list">{prompts.map((prompt) => <button key={prompt} className="prompt-pill" onClick={() => ask(prompt)}>{prompt}<ArrowUpRight size={13} /></button>)}</div>
        {answer && <AnswerCard answer={answer} />}
        {chat.isPending && <div className="chat-loading"><span className="spinner" /> Checking your academic sources…</div>}
        {chat.error && <ErrorNotice error={chat.error as Error} />}
        <form className="assistant-input" onSubmit={(event) => { event.preventDefault(); ask(); }}>
          <label className="sr-only" htmlFor="assistant-question">Ask CampusFlow</label><input id="assistant-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about deadlines, classes, or what changed…" />
          <button className="send-button" type="submit" disabled={chat.isPending || question.trim().length < 2} aria-label="Ask question"><Send size={16} /></button>
        </form>
        <p className="assistant-note"><ShieldCheck size={13} /> Your answer separates verified facts, conflicts, assumptions, and suggestions.</p>
      </section>
    </div>
  </>;
}

function StatCard({ icon, label, value, note, tone, alert }: { icon: ReactNode; label: string; value: number; note: string; tone: string; alert?: boolean }) {
  return <article className={`stat-card ${alert ? "stat-alert" : ""}`}><div className={`stat-icon ${tone}`}>{icon}</div><p>{label}</p><div className="stat-value">{value}<span>{note}</span></div></article>;
}

function DeadlineRow({ assignment }: { assignment: Assignment }) {
  return <article className="deadline-row">
    <div className={`course-mark ${assignment.course.color}`}>{assignment.course.code.slice(0, 2)}</div>
    <div className="deadline-detail"><div><span className="course-code">{assignment.course.code}</span><span className="due-date">{dateLabel(assignment.due_at, { weekday: "short", month: "short", day: "numeric" })}</span></div><h3>{assignment.title}</h3><p>{assignment.estimated_hours}h estimated <span>·</span> {assignment.course.name}</p></div>
    <div className="deadline-badge"><Clock3 size={13} />{dateLabel(assignment.due_at, { month: "short", day: "numeric" })}</div>
  </article>;
}

function ConflictCard({ conflict, compact = false }: { conflict: Conflict; compact?: boolean }) {
  return <article className={`conflict-card ${compact ? "conflict-compact" : ""}`}>
    <div className="conflict-title"><span><CircleAlert size={16} /></span><div><strong>{conflict.assignment}</strong><Tag tone="amber">Conflict</Tag></div></div>
    <p>{conflict.message}</p>
    <div className="conflict-sources">{conflict.sources.map((source) => <div key={source.source_id}><span>{source.source_title}</span><b>{dateLabel(source.due_at)}</b><small>{source.source_id}</small></div>)}</div>
    {!compact && <p className="conflict-caveat">Not verified — check with your instructor before relying on a date.</p>}
  </article>;
}

function AnswerCard({ answer }: { answer: Answer }) {
  return <section className="answer-card">
    <div className="answer-intro"><span className="answer-icon"><Sparkles size={15} /></span><p>{answer.answer}</p></div>
    {!!answer.verified_facts.length && <div className="answer-section"><h4><CheckCircle2 size={14} /> Verified facts</h4>{answer.verified_facts.map((fact) => <div className="fact-row" key={fact.claim}><p>{fact.claim}</p><div>{fact.source_ids.map((id) => <span className="source-chip" key={id}>{id}</span>)}</div></div>)}</div>}
    {!!answer.conflicts.length && <div className="answer-section"><h4 className="amber-text"><CircleAlert size={14} /> Conflicting information</h4>{answer.conflicts.map((conflict) => <ConflictCard key={conflict.assignment_id} conflict={conflict} />)}</div>}
    {!!answer.assumptions.length && <div className="answer-section"><h4><Search size={14} /> Assumptions</h4>{answer.assumptions.map((item) => <p className="plain-bullet" key={item}>{item}</p>)}</div>}
    {!!answer.recommendations.length && <div className="answer-section"><h4><Sparkles size={14} /> Suggested next steps</h4>{answer.recommendations.map((item) => <p className="plain-bullet" key={item}>{item}</p>)}</div>}
    <div className="answer-footer">DETERMINISTIC DEMO <span>·</span> {answer.sources.map((source) => source.source_id).join(" · ")}</div>
  </section>;
}

function DeadlinesPage() {
  const { data, isLoading, error } = useDashboard();
  if (isLoading) return <PageLoading />;
  return <><SectionTitle eyebrow="YOUR SEMESTER" title="Deadlines" action={<Tag tone="green">LMS demo data</Tag>} />
    <ErrorNotice error={error as Error | null} />
    <div className="deadline-page-grid"><div className="panel">
      <div className="panel-heading"><div><p className="eyebrow">ALL COURSES</p><h2>Upcoming work</h2></div><span className="count-label">{data?.assignments.length ?? 0} items</span></div>
      <div className="deadline-list">{data?.assignments.map((item) => <DeadlineRow key={item.id} assignment={item} />)}</div>
    </div><div className="panel"><div className="panel-heading"><div><p className="eyebrow">SOURCE MONITOR</p><h2>What changed</h2></div></div>
      {data?.changes.map((item) => <div className="change-item" key={`${item.source_id}-${item.field}`}><span className="change-icon"><ArrowDownRight size={16} /></span><div><strong>{item.assignment}</strong><p>{changeValue(item.old_due_at, item.field)} <ArrowRight size={12} /> <b>{changeValue(item.new_due_at, item.field)}</b></p><small>{item.status.replaceAll("_", " ")} · {item.field.replaceAll("_", " ")} · Source {item.source_id}</small></div></div>)}
      {data?.conflicts.map((item) => <ConflictCard key={item.assignment_id} conflict={item} />)}
      {!data?.conflicts.length && !data?.changes.length && <p className="empty-message">No deadline changes detected.</p>}
    </div></div>
  </>;
}

function ChangeRadarPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ["radar"], queryFn: () => api<RadarData>("/api/radar") });
  const { data: dashboard } = useDashboard();
  const publish = useMutation({
    mutationFn: () => api<{ created: boolean }>("/api/demo/publish-notice", { method: "POST", body: "{}" }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["radar"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["sources"] }),
      ]);
    },
  });
  const reset = useMutation({
    mutationFn: () => api("/api/demo/reset", { method: "POST", body: "{}" }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["radar"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["sources"] }),
        queryClient.invalidateQueries({ queryKey: ["twin-preferences"] }),
        queryClient.invalidateQueries({ queryKey: ["twin-simulation"] }),
        queryClient.invalidateQueries({ queryKey: ["proposals"] }),
        queryClient.invalidateQueries({ queryKey: ["audit"] }),
      ]);
    },
  });
  const baseline = dashboard?.assignments.find((item) => item.id === 2);
  return <>
    <SectionTitle eyebrow="ACADEMIC CHANGE RADAR" title="What changed, and why" action={<Tag tone="green">Source-linked history</Tag>} />
    <p className="page-lead">CampusFlow keeps prior values and evidence. A new source can create a verified update, a disputed change, or an item awaiting confirmation — it never silently overwrites the record.</p>
    <ErrorNotice error={(error ?? publish.error ?? reset.error) as Error | null} />
    <section className="radar-demo panel">
      <div><p className="eyebrow">REPRODUCIBLE HACKATHON DEMO</p><h2>DBMS lab deadline · currently {baseline ? dateLabel(baseline.due_at) : "Oct 28"}</h2><p>The original LMS record stays intact. Publish a sample department notice for October 30 to see the disagreement and full evidence trail.</p></div>
      <div className="radar-actions">
        <button className="button button-primary" onClick={() => publish.mutate()} disabled={publish.isPending || data?.demo_notice_published}>{publish.isPending ? "Publishing…" : data?.demo_notice_published ? "Notice detected" : "Publish Oct 30 notice"}</button>
        <button className="button button-outline" onClick={() => { if (window.confirm("Reset the synthetic demo records and remove proposals/audit history?")) reset.mutate(); }} disabled={reset.isPending}>{reset.isPending ? "Resetting…" : "Reset demo"}</button>
      </div>
    </section>
    <div className="radar-summary-grid">
      <section className="panel">
        <div className="panel-heading"><div><p className="eyebrow">COMPLETE HISTORY</p><h2>Change timeline</h2></div><Tag>{data?.history.length ?? 0} records</Tag></div>
        {isLoading ? <PageLoading /> : data?.history.length ? <div className="radar-timeline">{data.history.map((event) => <article className="radar-event" key={event.id}><span className={`timeline-marker marker-${event.status}`} /><div className="radar-event-content"><div className="radar-event-heading"><div><Tag tone={event.status === "verified" ? "green" : event.status === "disputed" ? "amber" : "default"}>{event.status.replaceAll("_", " ")}</Tag><span className="radar-event-date">{dateTime(event.detected_at)}</span></div><span className="radar-field">{event.field.replaceAll("_", " ")}</span></div><h3>{event.assignment}</h3><div className="change-values"><div><small>PREVIOUS VALUE</small><strong>{changeValue(event.old_value, event.field)}</strong></div><ArrowRight size={15} /><div><small>NEW VALUE</small><strong>{changeValue(event.new_value, event.field)}</strong></div></div><p className="radar-source">Detected from <b>{event.source_id}</b></p><div className="radar-source-evidence">{event.evidence_ids.map((id) => { const source = data.sources.find((item) => item.source_id === id); return <details key={id}><summary>{id}{source ? ` · ${source.title}` : ""}</summary>{source && <><p>{source.content}</p><small>{source.type} · Published {dateTime(source.published_at)}</small></>}</details>; })}</div>{event.status === "disputed" && <p className="risk-uncertainty"><CircleAlert size={14} /> The original date remains on the assignment. Sources disagree; ask the instructor before treating either date as confirmed.</p>}</div></article>)}</div> : <p className="empty-message">No changes have been recorded.</p>}
      </section>
      <aside className="radar-side">
        <section className="panel"><div className="panel-heading"><div><p className="eyebrow">CURRENT DISAGREEMENTS</p><h2>Needs confirmation</h2></div><CircleAlert size={17} className="amber-text" /></div>{data?.conflicts.length ? data.conflicts.map((conflict) => <ConflictCard key={conflict.assignment_id} conflict={conflict} />) : <div className="radar-clear"><CheckCircle2 size={18} /><p>No source conflicts before the demo notice.</p></div>}</section>
        <section className="panel radar-evidence"><p className="eyebrow">EVIDENCE, NOT GUESSES</p><h2>What CampusFlow compares</h2><ul><li>Stable source ID and publication timestamp</li><li>Prior and new deadline values kept separately</li><li>Independent current records to mark a dispute</li><li>Confirmation status remains distinct from workload risk</li></ul><Link className="text-link" to="/sources">Inspect all source records <ArrowRight size={14} /></Link></section>
      </aside>
    </div>
  </>;
}

function DigitalTwinPage() {
  const queryClient = useQueryClient();
  const { data: preferences, isLoading: preferencesLoading, error: preferencesError } = useQuery({ queryKey: ["twin-preferences"], queryFn: () => api<TwinPreferences>("/api/twin/preferences") });
  const { data: dashboard } = useDashboard();
  const [availability, setAvailability] = useState<Record<string, number>>({});
  const [sessionMinutes, setSessionMinutes] = useState(60);
  const [importance, setImportance] = useState<Record<string, number>>({});
  const [lostHours, setLostHours] = useState(2);
  const [extraEnabled, setExtraEnabled] = useState(false);
  const [extraTitle, setExtraTitle] = useState("Additional lab report");
  const [extraDue, setExtraDue] = useState("2026-10-27");
  const [extraHours, setExtraHours] = useState(2);
  const [estimateId, setEstimateId] = useState("");
  const [increaseHours, setIncreaseHours] = useState(2);
  const [moveSessionId, setMoveSessionId] = useState("");
  const [moveToDate, setMoveToDate] = useState("2026-10-24");
  const [result, setResult] = useState<TwinResult | null>(null);

  useEffect(() => {
    if (preferences) {
      setAvailability(preferences.availability);
      setSessionMinutes(preferences.session_minutes);
      setImportance(preferences.importance);
      setMoveSessionId(preferences.planned_sessions[0]?.id ?? "");
    }
  }, [preferences]);

  const save = useMutation({
    mutationFn: () => api<TwinPreferences>("/api/twin/preferences", { method: "PUT", body: JSON.stringify({ availability, session_minutes: sessionMinutes, importance }) }),
    onSuccess: async (updated) => {
      setAvailability(updated.availability);
      await queryClient.invalidateQueries({ queryKey: ["twin-preferences"] });
      run.mutate(scenario);
    },
  });
  const scenario: TwinScenario = {
    lost_hours_tomorrow: lostHours,
    ...(extraEnabled ? { additional_assignment: { title: extraTitle, due_date: extraDue, estimated_hours: extraHours } } : {}),
    ...(estimateId ? { increase_estimate: { assignment_id: Number(estimateId), extra_hours: increaseHours } } : {}),
    ...(moveSessionId ? { move_session: { session_id: moveSessionId, to_date: moveToDate } } : {}),
  };
  const run = useMutation({
    mutationFn: (input: TwinScenario) => api<TwinResult>("/api/twin/simulate", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: setResult,
  });
  const propose = useMutation({
    mutationFn: () => api<Proposal>("/api/twin/proposals", { method: "POST", body: JSON.stringify(scenario) }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["proposals"] });
      await queryClient.invalidateQueries({ queryKey: ["audit"] });
    },
  });
  const displayedDates = Object.keys(availability).sort().slice(0, 7);
  const currentResult = result;
  return <>
    <SectionTitle eyebrow="ACADEMIC DIGITAL TWIN" title="Try a different week" action={<Tag tone="green"><SlidersHorizontal size={13} /> Deterministic simulator</Tag>} />
    <p className="page-lead">Change the inputs and see the schedule recompute. This transparent workload model does not estimate grades or guarantee outcomes.</p>
    <ErrorNotice error={(preferencesError ?? save.error ?? run.error ?? propose.error) as Error | null} />
    <div className="twin-grid">
      <section className="panel twin-controls">
        <div className="panel-heading"><div><p className="eyebrow">YOUR CONSTRAINTS</p><h2>Study availability</h2></div><CalendarDays size={17} /></div>
        {preferencesLoading ? <PageLoading /> : <>
          <p className="control-hint">Focused hours you can study. Unspecified dates are treated as zero hours.</p>
          <div className="availability-grid">{displayedDates.map((day) => <label key={day}><span>{dateLabel(`${day}T12:00:00`, { weekday: "short", month: "short", day: "numeric" })}</span><div><input aria-label={`Available hours ${day}`} type="number" min="0" max="16" step="0.5" value={availability[day] ?? 0} onChange={(event) => setAvailability({ ...availability, [day]: Number(event.target.value) })} /><small>hours</small></div></label>)}</div>
          <label className="control-label" htmlFor="session-length">Preferred focus session</label><select id="session-length" value={sessionMinutes} onChange={(event) => setSessionMinutes(Number(event.target.value))}><option value={25}>25 minutes</option><option value={45}>45 minutes</option><option value={60}>60 minutes</option><option value={90}>90 minutes</option><option value={120}>120 minutes</option></select>
          <div className="importance-settings"><p className="eyebrow">OPTIONAL STUDENT-PROVIDED IMPORTANCE</p>{dashboard?.assignments.map((item) => <label key={item.id}><span>{item.course.code} · {item.title}</span><select aria-label={`Importance for ${item.title}`} value={importance[String(item.id)] ?? ""} onChange={(event) => setImportance({ ...importance, [String(item.id)]: Number(event.target.value) })}><option value="">Not set</option><option value="1">1 · Low</option><option value="2">2</option><option value="3">3 · Usual</option><option value="4">4</option><option value="5">5 · High</option></select></label>)}</div>
          <div className="planned-session-box"><p className="eyebrow">EXISTING PLANNED SESSION</p>{preferences?.planned_sessions.length ? preferences.planned_sessions.map((session) => <div className="planned-session-line" key={session.id}><span>{dashboard?.assignments.find((item) => item.id === session.assignment_id)?.title ?? "Study session"} · {session.minutes}m · {dateLabel(`${session.date}T12:00:00`)}</span><Tag tone="green">Reserved</Tag></div>) : <p className="control-hint">No existing sessions.</p>}</div>
        </>}
      </section>
      <section className="panel scenario-controls">
        <div className="panel-heading"><div><p className="eyebrow">WHAT-IF SCENARIOS</p><h2>Stress-test the week</h2></div><Activity size={17} /></div>
        <label className="scenario-label" htmlFor="lost-hours">Lose study time tomorrow <strong>{lostHours}h</strong></label><input id="lost-hours" type="range" min="0" max="4" step="0.5" value={lostHours} onChange={(event) => setLostHours(Number(event.target.value))} /><p className="control-hint">Tomorrow is Saturday, October 24 in this reproducible demo.</p>
        <label className="scenario-toggle"><input type="checkbox" checked={extraEnabled} onChange={(event) => setExtraEnabled(event.target.checked)} /><span><strong>Add an assignment</strong><small>Simulation only; it won’t be saved.</small></span></label>
        {extraEnabled && <div className="scenario-fields"><input aria-label="Additional assignment title" value={extraTitle} onChange={(event) => setExtraTitle(event.target.value)} /><label>Due <input type="date" value={extraDue} onChange={(event) => setExtraDue(event.target.value)} /></label><label>Hours <input type="number" min="0.5" max="100" step="0.5" value={extraHours} onChange={(event) => setExtraHours(Number(event.target.value))} /></label></div>}
        <label className="control-label" htmlFor="increase-task">Discover more work required</label><div className="inline-fields"><select id="increase-task" value={estimateId} onChange={(event) => setEstimateId(event.target.value)}><option value="">No estimate change</option>{dashboard?.assignments.map((item) => <option key={item.id} value={item.id}>{item.course.code} · {item.title}</option>)}</select>{estimateId && <input aria-label="Additional estimated hours" type="number" min="0.5" max="100" step="0.5" value={increaseHours} onChange={(event) => setIncreaseHours(Number(event.target.value))} />}</div>
        <label className="control-label" htmlFor="move-session">Move an existing session</label><div className="inline-fields"><select id="move-session" value={moveSessionId} onChange={(event) => setMoveSessionId(event.target.value)}><option value="">Keep current sessions</option>{preferences?.planned_sessions.map((session) => <option value={session.id} key={session.id}>{dashboard?.assignments.find((item) => item.id === session.assignment_id)?.title} · {dateLabel(`${session.date}T12:00:00`)}</option>)}</select>{moveSessionId && <input aria-label="Move session to date" type="date" value={moveToDate} onChange={(event) => setMoveToDate(event.target.value)} />}</div>
        <div className="twin-actions"><button className="button button-outline" onClick={() => save.mutate()} disabled={save.isPending || preferencesLoading}>{save.isPending ? "Saving…" : "Save my inputs"}</button><button className="button button-primary" onClick={() => run.mutate(scenario)} disabled={run.isPending || preferencesLoading}><Activity size={15} />{run.isPending ? "Recalculating…" : "Simulate changes"}</button></div>
      </section>
    </div>
    {currentResult && <section className="twin-results">
      <div className="panel twin-result-heading"><div><p className="eyebrow">EXPLAINABLE RISK ENGINE</p><h2>Here’s what changes in this scenario</h2><p>{currentResult.summary.remaining_work_hours}h estimated work left · {currentResult.summary.available_capacity_hours}h free capacity · {currentResult.summary.fits ? "All work fits under current assumptions" : "Some work doesn’t fit before deadlines"}</p></div><button className="button button-primary" onClick={() => propose.mutate()} disabled={propose.isPending}>{propose.isPending ? "Creating proposal…" : <><Plus size={15} /> Review revised plan</>}</button></div>
      <ErrorNotice error={propose.error as Error | null} />
      {propose.isSuccess && <div className="success-notice"><CheckCircle2 size={15} /> Proposal saved as pending review. No calendar was changed. <Link to="/study-plan">Open study plans <ArrowRight size={13} /></Link></div>}
      <div className="risk-list">{currentResult.risks.map((risk) => <article className="panel risk-card" key={risk.assignment_id}><div className="risk-head"><div><span className="course-code">{risk.course}</span><h3>{risk.assignment}</h3></div><div className="risk-score-wrap"><Tag tone={risk.status === "At risk" ? "amber" : risk.status === "Needs attention" ? "default" : "green"}>{risk.status}</Tag><strong>{risk.priority_score}<small>/100</small></strong></div></div><div className="risk-meter"><span style={{ width: `${risk.priority_score}%` }} /></div><p className="risk-explanation">{risk.explanation}</p><div className="risk-factors"><span>Workload <b>{risk.workload_score}</b></span><span>Uncertainty <b>+{risk.uncertainty_points}</b></span><span>Effort <b>{risk.estimated_hours_remaining}h</b></span><span>Capacity <b>{risk.available_hours_before_due}h</b></span></div>{risk.deadline_uncertainty.status !== "none" && <p className="risk-uncertainty"><CircleAlert size={14} />{risk.deadline_uncertainty.explanation} Window {dateLabel(`${risk.deadline_uncertainty.window_start}T12:00:00`)}–{dateLabel(`${risk.deadline_uncertainty.window_end}T12:00:00`)} · {risk.deadline_uncertainty.source_ids.join(", ")}</p>}</article>)}</div>
      <div className="twin-result-grid"><section className="panel"><div className="panel-heading"><div><p className="eyebrow">REVISED SCHEDULE</p><h2>Study blocks by day</h2></div></div>{currentResult.schedule.map((day) => <div className="schedule-day" key={day.date}><div><strong>{dateLabel(`${day.date}T12:00:00`, { weekday: "short", month: "short", day: "numeric" })}</strong><small>{day.available_hours}h availability</small></div><div>{day.sessions.map((session, index) => <div className="schedule-session" key={`${session.assignment_id}-${index}`}><span>{session.course}</span><p>{session.assignment}</p><small>{session.minutes}m {session.existing ? "· existing" : "· proposed"}</small></div>)}</div></div>)}{currentResult.unscheduled.length > 0 && <div className="unscheduled-list"><h3>May not fit before deadline</h3>{currentResult.unscheduled.map((item) => <p key={item.assignment_id}><CircleAlert size={14} />{item.assignment}: {item.unscheduled_hours}h unscheduled · planning boundary {dateLabel(`${item.due_at}T12:00:00`)}</p>)}</div>}</section><aside className="panel explain-panel"><p className="eyebrow">ASSUMPTIONS & ALTERNATIVES</p><h2>How to read this</h2><ul>{currentResult.assumptions.map((item) => <li key={item}>{item}</li>)}</ul><h3>Alternatives</h3><ul>{currentResult.alternatives.map((item) => <li key={item}>{item}</li>)}</ul><p className="risk-disclaimer">Priorities are transparent rules, not predictions about grades or guaranteed outcomes.</p></aside></div>
    </section>}
  </>;
}

function SourcesPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["sources"], queryFn: () => api<Source[]>("/api/notices") });
  const [filter, setFilter] = useState("all");
  if (isLoading) return <PageLoading />;
  const filtered = (data ?? []).filter((source) => filter === "all" || source.type === filter);
  return <><SectionTitle eyebrow="YOUR CONNECTED CONTEXT" title="Notices & sources" action={<Tag tone="green">Synthetic records</Tag>} />
    <ErrorNotice error={error as Error | null} />
    <div className="filter-row">{["all", "lms", "notice", "email"].map((kind) => <button key={kind} className={`filter-button ${filter === kind ? "selected" : ""}`} onClick={() => setFilter(kind)}>{kind === "all" ? "All sources" : kind.toUpperCase()}</button>)}</div>
    <div className="source-list">{filtered.map((source) => <article className="source-card" key={source.source_id}><div className="source-card-head"><span className={`source-type source-${source.type}`}>{source.type === "lms" ? <BookOpen size={14} /> : source.type === "email" ? <MessageCircle size={14} /> : <FileText size={14} />}{source.type}</span><span className="source-date">{dateTime(source.published_at)}</span></div><h2>{source.title}</h2><p>{source.content}</p><div className="source-card-foot"><span>{source.source_id}</span><Tag tone={source.verified ? "green" : "amber"}>{source.verified ? "Source verified" : "Unverified"}</Tag></div></article>)}</div>
  </>;
}

function StudyPlanPage() {
  const queryClient = useQueryClient();
  const { data: proposals, isLoading, error } = useQuery({ queryKey: ["proposals"], queryFn: () => api<Proposal[]>("/api/proposals") });
  const create = useMutation({ mutationFn: () => api<Proposal>("/api/proposals", { method: "POST" }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["proposals"] }) });
  const decide = useMutation({ mutationFn: ({ id, approved }: { id: number; approved: boolean }) => api<Proposal>(`/api/proposals/${id}/decision`, { method: "POST", body: JSON.stringify({ approved }) }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["proposals"] }) });
  return <><SectionTitle eyebrow="MAKE A LITTLE SPACE" title="Your study plan" action={<button className="button button-primary" onClick={() => create.mutate()} disabled={create.isPending}><Plus size={16} />{create.isPending ? "Building…" : "Suggest a plan"}</button>} />
    <p className="page-lead">A practical starting point based on upcoming workload. Plans are proposals — they never change your calendar unless you choose to take action.</p>
    <ErrorNotice error={(error ?? create.error ?? decide.error) as Error | null} />
    {isLoading ? <PageLoading /> : <div className="plan-list">{proposals?.map((proposal) => <article className="panel plan-card" key={proposal.id}><div className="panel-heading"><div><p className="eyebrow">{proposal.kind === "revised_study_plan" ? "DIGITAL TWIN PROPOSAL" : "STUDY PLAN PROPOSAL"}</p><h2>{proposal.title}</h2></div><Tag tone={proposal.status === "pending" ? "amber" : proposal.status === "approved" ? "green" : "default"}>{proposal.status}</Tag></div><p className="plan-note"><ShieldCheck size={15} />{proposal.payload.notice}</p>
      {proposal.payload.sessions && <div className="plan-sessions">{proposal.payload.sessions.map((item) => <div className="plan-session" key={`${proposal.id}-${item.assignment}`}><span className="session-day">DAY {item.day}</span><div><strong>{item.assignment}</strong><p>{item.course} · {item.minutes} minutes{item.due_at ? ` · due ${dateLabel(item.due_at)}` : ""}</p><small>{item.focus}</small></div><ChevronRight size={16} /></div>)}</div>}
      {proposal.payload.schedule && <div className="plan-sessions">{proposal.payload.schedule.map((day) => <div className="revised-plan-day" key={`${proposal.id}-${day.date}`}><strong>{dateLabel(`${day.date}T12:00:00`, { weekday: "short", month: "short", day: "numeric" })}</strong><div>{day.sessions.map((session, index) => <p key={`${session.assignment_id}-${index}`}><b>{session.course}</b> · {session.assignment} · {session.minutes}m {session.existing ? "(existing)" : "(proposed)"}</p>)}</div></div>)}</div>}
      {proposal.payload.risks && <div className="proposal-risk-summary">{proposal.payload.risks.slice(0, 4).map((risk) => <p key={risk.assignment_id}><Tag tone={risk.status === "At risk" ? "amber" : "green"}>{risk.status}</Tag> {risk.assignment} · priority {risk.priority_score}/100 · uncertainty +{risk.uncertainty_points}</p>)}</div>}
      {proposal.payload.unscheduled?.length ? <div className="unscheduled-list"><h3>Still needs time</h3>{proposal.payload.unscheduled.map((item) => <p key={item.assignment_id}><CircleAlert size={14} />{item.assignment}: {item.unscheduled_hours}h unscheduled.</p>)}</div> : null}
      {proposal.payload.assumptions && <details className="proposal-assumptions"><summary>Simulation assumptions</summary><ul>{proposal.payload.assumptions.map((item) => <li key={item}>{item}</li>)}</ul></details>}
      {proposal.payload.outcome && <p className="plan-note"><CheckCircle2 size={14} /> Outcome: {proposal.payload.outcome.replaceAll("_", " ")}</p>}
      {proposal.status === "pending" && <div className="proposal-actions"><span>Review before approving</span><button className="button button-outline" onClick={() => decide.mutate({ id: proposal.id, approved: false })}>Decline</button><button className="button button-primary" onClick={() => decide.mutate({ id: proposal.id, approved: true })}><Check size={15} /> Approve plan</button></div>}</article>)}
      {!proposals?.length && <div className="empty-panel"><span><BookOpen size={23} /></span><h2>No plan yet</h2><p>Generate a personalized proposal from your upcoming assignments.</p><button className="button button-primary" onClick={() => create.mutate()} disabled={create.isPending}><Sparkles size={15} /> Create a study plan</button></div>}</div>}
  </>;
}

function ActivityPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["audit"], queryFn: () => api<Audit[]>("/api/audit") });
  return <><SectionTitle eyebrow="TRANSPARENCY BY DEFAULT" title="Activity log" action={<Tag tone="green"><ShieldCheck size={13} /> Private to you</Tag>} /><p className="page-lead">A record of proposals and decisions made in this workspace. Prompts and private source contents are not stored here.</p><ErrorNotice error={error as Error | null} />
    <div className="panel audit-panel">{isLoading ? <PageLoading /> : data?.length ? data.map((item) => <div className="audit-row" key={item.id}><span className="audit-icon"><Activity size={15} /></span><div><strong>{item.action.replaceAll("_", " ")}</strong><p>{item.entity_type} · #{item.entity_id}</p></div><time>{dateTime(item.created_at)}</time></div>) : <p className="empty-message">No actions recorded yet.</p>}</div>
  </>;
}

export default function App() {
  const [username, setUsername] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  useEffect(() => {
    api<{ authenticated: boolean; username?: string }>("/api/session")
      .then((session) => { if (session.authenticated) setUsername(session.username ?? "Student"); })
      .catch(() => setUsername(null))
      .finally(() => setChecking(false));
  }, []);
  async function logout() {
    await api("/api/logout", { method: "POST", body: "{}" });
    setUsername(null);
    queryClient.clear();
    navigate("/");
  }
  if (checking) return <PageLoading />;
  return username ? <AppShell username={username} onLogout={() => { void logout(); }} /> : <SignIn onSignedIn={setUsername} />;
}
