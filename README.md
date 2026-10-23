# CampusFlow

CampusFlow is a self-hosted ambient academic assistant for engineering students. It brings course deadlines and synthetic LMS, email, and notice records into one evidence-aware workspace; compares versioned academic records; explains workload risk; and proposes study plans that require an explicit approval decision.

The complete demo runs without a paid AI API. Chat uses deterministic, rule-based responses and clearly labels verified facts, conflicting sources, assumptions, and suggested next steps. The optional Gmail and Google Calendar connectors are not connected in this demo; the UI marks them as unavailable rather than implying live access. All sample academic records are fictional.

## Features

- Student dashboard with course cards, upcoming work, deadline updates, and source conflicts.
- Academic chat with source IDs, verified facts, unresolved conflicts, assumptions, and recommendations.
- Academic Change Radar compares stored source versions for deadlines, examination dates, assignment requirements, and notices. It shows old/new values, evidence, timestamps, and whether a change is verified, disputed, or awaiting confirmation.
- Deadline-change detection and conflict detection compare current records from independent source types without silently overwriting the original assignment deadline.
- Explainable Digital Twin simulates lost availability, added work, changed effort estimates, and moved study sessions using deterministic scheduling. It exposes assumptions, work capacity, unscheduled effort, and deadline uncertainty separately from workload risk.
- Explainable risk scores show urgency, work remaining, available capacity, explicitly provided importance, and a distinct uncertainty contribution; they are not grade predictions.
- Evidence-to-action workflow connects changed records to recalculated risks and a revised plan. The plan remains pending until the student reviews it; approval is audited and does not write to an external calendar.
- Searchable/filterable synthetic LMS, email, and department-notice records.
- Study-plan proposals from assignment effort and due-date order. Plans remain pending until approved or declined and do not write to a calendar.
- A self-hosted MCP server using the official Python SDK's Streamable HTTP transport and bearer authentication. Its tools list deadlines, compare changes/conflicts, search academic sources, and create pending study-plan proposals.
- An append-only audit history for proposal creation and decisions; prompts and source contents are not logged.
- Signed, HTTP-only browser sessions; same-origin checks, login attempt limiting, security headers, and protected academic APIs.
- PostgreSQL persistence with Alembic schema migrations; SQLite is used for a zero-setup local demo.
- React + TypeScript + Vite frontend using React Router, TanStack Query, and Tailwind CSS.

## Architecture

```text
React/Vite browser
  └─ FastAPI :8000
       ├─ SQLAlchemy ── SQLite (local) or PostgreSQL (Compose)
       └─ academic rule engine

MCP client ── Streamable HTTP + bearer token ── MCP server :8001/mcp
                                                   └─ academic tools ── same database
```

The API provides FastAPI OpenAPI docs at `/docs`. MCP uses the official Python SDK `FastMCP` and `streamable_http_app()` server APIs and the MCP Streamable HTTP transport. MCP tools are read-only except `record_academic_update`, which adds a source record and change history, and study-plan proposal tools, which create a pending proposal only. No tool edits external systems.

An optional OpenAI-compatible chat-completions provider can rephrase the rule-based analysis. Set `MODEL_API_KEY`, `MODEL_BASE_URL`, and `MODEL_NAME` in `.env` to enable it. With a key configured, provider failures are reported as errors rather than being disguised as a successful deterministic response. Only enable a hosted provider after reviewing its privacy and retention terms.

## Requirements and compatible versions

- Python 3.11 or newer.
- Node.js 20 or newer and npm.
- Docker Desktop / Docker Compose v2 for the PostgreSQL option.
- No API key or external service is required for the demo.

Dependency ranges are declared in `requirements.txt` / `requirements-dev.txt` and `frontend/package.json`. The project uses FastAPI 0.115+, Pydantic 2 (through FastAPI), SQLAlchemy 2, Alembic 1.13+, psycopg 3, MCP Python SDK 1.12+, React 19, TypeScript 5.8, Vite 6, React Router 7, TanStack Query 5, and Tailwind CSS 4.

## Run locally

In PowerShell, from the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Edit `.env`: set a unique `APP_PASSWORD` (at least 16 characters), `SESSION_SECRET` and `MCP_BEARER_TOKEN` (at least 32 characters each). Keep `APP_ALLOWED_ORIGINS` set to the local Vite dev URL for local development. For a reverse-proxied deployment, replace it with the exact trusted frontend origin(s); same-origin requests need no allowlist entry. Do not commit `.env`. For example, generate secrets with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

The default `DATABASE_URL=sqlite:///./campusflow.db` starts a local persistent demo database. The API creates the initial schema and seeds fictional course data the first time it runs. When upgrading an existing database, apply migrations before starting the API:

```powershell
alembic upgrade head
```

Leave `MODEL_API_KEY` blank to use the deterministic local demo.

Install and start the frontend:

```powershell
Set-Location frontend
npm install
npm run dev
```

Start the API in another PowerShell terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m backend.main
```

Start the MCP server in a third PowerShell terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m backend.mcp_server
```

Open <http://127.0.0.1:5173> and sign in using the configured `APP_USERNAME` and `APP_PASSWORD`. The Vite dev server proxies `/api` requests to FastAPI. The MCP server listens on <http://127.0.0.1:8001/mcp>; FastAPI docs are at <http://127.0.0.1:8000/docs>.

For a production-like single-origin local run, build the frontend first (`Set-Location frontend; npm run build`) and then run the API; FastAPI serves `frontend/dist`.

## Run with Docker Compose

Copy and edit `.env.example` as `.env`, set strong unique application/MCP secrets, then run from the repository root:

```powershell
docker compose up --build
```

Compose runs PostgreSQL 16, applies Alembic migrations before starting FastAPI, and runs the MCP server against the same database. The app is at <http://127.0.0.1:8000>, the MCP endpoint at <http://127.0.0.1:8001/mcp>. Both published ports are bound to loopback. The sample Compose Postgres password is for local development only; replace it before sharing or deploying. Persistent PostgreSQL data is held in the `campusflow-postgres` volume.

To apply later schema migrations against the configured database:

```powershell
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

## MCP tools

The authenticated MCP tool catalog includes:

| Tool | Purpose |
| --- | --- |
| `list_upcoming_deadlines` | List assignments, course details, effort estimates, and due dates. |
| `detect_deadline_changes_and_conflicts` | Return verified historical changes separately from unresolved date disagreements. |
| `get_academic_change_history` | Return the complete academic change timeline with values, statuses, and evidence IDs. |
| `record_academic_update` | Add a typed source version (deadline, examination date, assignment requirement, or notice) and compare it with prior versions. |
| `publish_signature_demo_notice` | Add the synthetic Oct 30 DBMS notice while preserving the original LMS deadline. |
| `simulate_academic_workload` | Recalculate schedule fit, risks, and assumptions for a lost-time scenario. |
| `propose_revised_study_plan` | Create a pending plan proposal from a digital-twin scenario. |
| `search_academic_sources` | Search synthetic LMS, email, and notice records with stable evidence IDs. |
| `propose_study_plan` | Create a pending, auditable study-plan proposal without writing to a calendar. |

The MCP service requires a bearer token set in `MCP_BEARER_TOKEN`. Keep it on a private network; do not publish it directly to the internet.

## Signature intelligence-layer demo

Reset the synthetic data from the **Change Radar** page before each walkthrough. The seed has a DBMS assignment due October 28 in its LMS source, and no Oct 30 notice yet. The reproducible workflow is:

1. Open **Change Radar** and confirm the baseline history and absence of a DBMS conflict.
2. Select **Publish Oct 30 notice**. CampusFlow adds a second source version while retaining the Oct 28 LMS value, then marks the mismatch disputed and exposes both source records, timestamps, and evidence.
3. Open **Digital Twin**. The risk breakdown keeps the disputed due-date window separate from workload risk and explains its conservative planning boundary.
4. Simulate losing two study hours tomorrow. The deterministic scheduler recalculates capacity, sessions, urgency, and any work that no longer fits, with assumptions and alternatives visible.
5. Generate a revised-plan proposal and review the schedule/risk explanation. Explicitly approve or decline it; approval only records the decision and never changes an external calendar.
6. Use **Reset demo** to restore the Oct 28 baseline and clear demo proposals and audit history.

For other record types, the authenticated API endpoint `POST /api/radar/records` accepts a stable `record_key`, typed `record_kind`, value, source metadata, and evidence content. The same operation is available as the `record_academic_update` MCP tool. Each new version is compared with stored history; independent disagreement stays visible as disputed, and a single new source awaits confirmation. This version-aware evidence trail, transparent workload simulation, and approval boundary distinguish CampusFlow from a chatbot, calendar, or task list.

## Tests

Run backend tests:

```powershell
python -m pytest -q
```

Run frontend component tests and a production type-check/build:

```powershell
Set-Location frontend
npm test
npm run build
```

Tests exercise deadline, examination-date, and requirement version changes; evidence/conflict classification; digital-twin what-if simulations; protected API behavior; approval/audit state; MCP Streamable HTTP discovery and input validation; and frontend sign-in behavior. They use synthetic data and do not contact hosted AI providers or real student systems.

## Security and demo limitations

- The seeded student, assignments, notices, and emails are invented; no college LMS, Gmail, or Google Calendar account is accessed.
- Facts are source-backed where records exist. Different current dates remain marked as conflicts; CampusFlow does not silently choose an authority.
- Rule-based responses are deterministic demo output, not a general-purpose language model. Verify important academic dates with instructors.
- Study plans are recommendations. Approval records the student's decision but does not automatically schedule or submit anything.
- Login limiting is in-memory and suitable only for a single-process demo. A shared/public deployment needs TLS, secure secret management, a production-grade identity provider, and distributed abuse controls.
- Before adding live integrations or hosted models, obtain student consent and review provider data-retention, FERPA/privacy, access-control, and deletion requirements.
