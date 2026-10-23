from __future__ import annotations

import hmac
import logging
import time
from collections import defaultdict, deque
from datetime import date, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from backend import academic
from backend.ai import AIProviderError, summarize_with_provider
from backend.config import PROJECT_ROOT, settings
from backend.db import get_db
from backend.models import ActionProposal, AuditEvent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("campusflow.audit")
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
LOGIN_WINDOW_SECONDS = 300
LOGIN_ATTEMPT_LIMIT = 5
login_attempts: dict[str, deque[float]] = defaultdict(deque)

app = FastAPI(title="CampusFlow API", version="1.0.0", description="Evidence-aware academic assistant for engineering students.")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="campusflow_session",
    same_site="strict",
    https_only=settings.cookie_secure,
    max_age=8 * 60 * 60,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; "
        "base-uri 'self'; form-action 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2000)


class AcademicRecordRequest(BaseModel):
    record_key: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9:_-]+$")
    record_kind: Literal["deadline", "examination_date", "assignment_requirement", "notice"]
    record_value: str = Field(min_length=1, max_length=2000)
    source_id: str = Field(min_length=2, max_length=40)
    source_title: str = Field(min_length=2, max_length=180)
    source_type: Literal["lms", "email", "notice", "calendar"]
    content: str = Field(min_length=2, max_length=10000)
    published_at: datetime | None = None

    @model_validator(mode="after")
    def validate_date_value(self):
        if self.record_kind in {"deadline", "examination_date"}:
            try:
                date.fromisoformat(self.record_value[:10])
            except ValueError as error:
                raise ValueError("Deadline and examination values must start with an ISO date") from error
        return self


class DecisionRequest(BaseModel):
    approved: bool


class AdditionalAssignment(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    due_date: date
    estimated_hours: float = Field(gt=0, le=100)
    course_code: str = Field(default="EXTRA", min_length=2, max_length=20)
    importance: int | None = Field(default=None, ge=1, le=5)


class EstimateChange(BaseModel):
    assignment_id: int = Field(gt=0)
    extra_hours: float = Field(gt=0, le=100)


class SessionMove(BaseModel):
    session_id: str = Field(min_length=1, max_length=80)
    to_date: date


class TwinScenarioRequest(BaseModel):
    lost_hours_tomorrow: float = Field(default=0, ge=0, le=16)
    additional_assignment: AdditionalAssignment | None = None
    increase_estimate: EstimateChange | None = None
    move_session: SessionMove | None = None


class TwinPreferencesRequest(BaseModel):
    availability: dict[str, float]
    session_minutes: int = Field(ge=25, le=180)
    importance: dict[str, int] = Field(default_factory=dict)

    @field_validator("availability")
    @classmethod
    def validate_availability(cls, value: dict[str, float]) -> dict[str, float]:
        if len(value) > 31:
            raise ValueError("Availability can cover at most 31 dates")
        for date_text, hours in value.items():
            date.fromisoformat(date_text)
            if not 0 <= hours <= 16:
                raise ValueError("Available study hours must be between 0 and 16 per day")
        return value

    @field_validator("importance")
    @classmethod
    def validate_importance(cls, value: dict[str, int]) -> dict[str, int]:
        if any(not key.isdigit() or not 1 <= score <= 5 for key, score in value.items()):
            raise ValueError("Importance must map assignment IDs to scores from 1 through 5")
        return value


def _authenticated_user(request: Request) -> str:
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Please sign in to continue")
    return username


academic.initialize_database()


def _check_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    parsed = urlsplit(origin)
    normalized_origin = f"{parsed.scheme}://{parsed.netloc}".casefold()
    is_same_origin = (
        parsed.scheme.casefold() == request.url.scheme.casefold()
        and parsed.netloc.casefold() == request.url.netloc.casefold()
    )
    is_allowed_origin = normalized_origin in settings.allowed_origins
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or not (is_same_origin or is_allowed_origin)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-origin request denied")


def _is_rate_limited(remote_address: str) -> bool:
    now = time.monotonic()
    attempts = login_attempts[remote_address]
    while attempts and now - attempts[0] > LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    return len(attempts) >= LOGIN_ATTEMPT_LIMIT


@app.get("/api/health")
async def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok", "mode": "deterministic_demo"}


@app.post("/api/login")
async def login(payload: LoginRequest, request: Request) -> dict[str, str]:
    _check_same_origin(request)
    remote_address = request.client.host if request.client else "unknown"
    if _is_rate_limited(remote_address):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    valid_username = hmac.compare_digest(payload.username, settings.username)
    valid_password = hmac.compare_digest(payload.password, settings.password)
    if not (valid_username and valid_password):
        login_attempts[remote_address].append(time.monotonic())
        logger.warning("audit event=login actor=unknown outcome=failure")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    login_attempts.pop(remote_address, None)
    request.session.clear()
    request.session["username"] = settings.username
    logger.info("audit event=login actor=%s outcome=success", settings.username)
    return {"username": settings.username}


@app.post("/api/logout")
async def logout(request: Request) -> dict[str, str]:
    _check_same_origin(request)
    request.session.clear()
    return {"status": "logged_out"}


@app.get("/api/session")
async def get_session(request: Request) -> dict[str, str | bool]:
    username = request.session.get("username")
    if not username:
        return {"authenticated": False}
    return {"authenticated": True, "username": username}


@app.get("/api/dashboard")
async def get_dashboard(request: Request, db: Session = Depends(get_db)) -> dict:
    _authenticated_user(request)
    return academic.dashboard(db)


@app.get("/api/assignments")
async def get_assignments(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    _authenticated_user(request)
    return academic.list_assignments(db)


@app.get("/api/radar")
async def get_change_radar(request: Request, db: Session = Depends(get_db)) -> dict:
    _authenticated_user(request)
    return {
        "history": academic.change_history(db),
        "conflicts": academic.deadline_conflicts(db),
        "sources": academic.list_sources(db),
        "demo_notice_published": any(source["source_id"] == "NOTICE-CS315-18" for source in academic.list_sources(db)),
    }


@app.post("/api/radar/records")
async def post_academic_record(
    payload: AcademicRecordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    _check_same_origin(request)
    actor = _authenticated_user(request)
    published_at = payload.published_at or academic.NOW
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=academic.NOW.tzinfo)
    try:
        result = academic.ingest_academic_record(
            db,
            record_key=payload.record_key,
            record_kind=payload.record_kind,
            record_value=payload.record_value,
            source_id=payload.source_id,
            source_title=payload.source_title,
            source_type=payload.source_type,
            content=payload.content,
            published_at=published_at,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    logger.info("audit event=academic_record_ingested actor=%s source_id=%s changed=%s", actor, payload.source_id, result["changed"])
    return result


@app.post("/api/demo/publish-notice")
async def publish_demo_notice(request: Request, db: Session = Depends(get_db)) -> dict:
    _check_same_origin(request)
    actor = _authenticated_user(request)
    try:
        result = academic.publish_demo_notice(db)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    logger.info("audit event=demo_notice actor=%s outcome=%s source_id=%s", actor, "created" if result["created"] else "already_present", result["source_id"])
    return result


@app.post("/api/demo/reset")
async def reset_demo(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    _check_same_origin(request)
    actor = _authenticated_user(request)
    academic.reset_demo_data(db)
    logger.info("audit event=demo_reset actor=%s outcome=success", actor)
    return {"status": "reset", "notice_published": "false"}


@app.get("/api/twin/preferences")
async def get_twin_preferences(request: Request, db: Session = Depends(get_db)) -> dict:
    _authenticated_user(request)
    return academic.twin_preferences_data(db)


@app.put("/api/twin/preferences")
async def put_twin_preferences(payload: TwinPreferencesRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    _check_same_origin(request)
    _authenticated_user(request)
    return academic.update_twin_preferences(db, payload.availability, payload.session_minutes, payload.importance)


@app.post("/api/twin/simulate")
async def simulate_academic_twin(payload: TwinScenarioRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    _check_same_origin(request)
    _authenticated_user(request)
    try:
        return academic.simulate_workload(db, payload.model_dump(mode="json"))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/twin/proposals")
async def propose_revised_plan(payload: TwinScenarioRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    _check_same_origin(request)
    actor = _authenticated_user(request)
    try:
        proposal = academic.create_revised_plan(db, actor, payload.model_dump(mode="json"))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return academic.proposal_data(proposal)


@app.get("/api/notices")
async def get_notices(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    _authenticated_user(request)
    return academic.list_sources(db)


@app.post("/api/chat")
async def chat(payload: ChatRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    _check_same_origin(request)
    actor = _authenticated_user(request)
    result = academic.ask_academic_question(payload.message, db)
    if settings.model_api_key:
        try:
            result["answer"] = await summarize_with_provider(payload.message, result, settings)
            result["mode"] = "configured_model"
        except AIProviderError as error:
            logger.error("audit event=chat actor=%s outcome=failure error_type=%s", actor, type(error).__name__)
            raise HTTPException(status_code=502, detail="The configured AI provider could not complete the request.") from error
    logger.info("audit event=chat actor=%s outcome=success mode=%s", actor, result["mode"])
    return result


@app.get("/api/proposals")
async def get_proposals(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    _authenticated_user(request)
    proposals = db.scalars(select(ActionProposal).order_by(ActionProposal.created_at.desc())).all()
    return [academic.proposal_data(item) for item in proposals]


@app.post("/api/proposals")
async def post_proposal(request: Request, db: Session = Depends(get_db)) -> dict:
    _check_same_origin(request)
    actor = _authenticated_user(request)
    proposal = academic.create_study_plan(db, actor)
    logger.info("audit event=proposal actor=%s outcome=pending proposal_id=%s", actor, proposal.id)
    return academic.proposal_data(proposal)


@app.post("/api/proposals/{proposal_id}/decision")
async def decide_action(proposal_id: int, payload: DecisionRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    _check_same_origin(request)
    actor = _authenticated_user(request)
    proposal = db.get(ActionProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "pending":
        raise HTTPException(status_code=409, detail="This proposal has already been decided")
    academic.decide_proposal(db, proposal, actor, payload.approved)
    if proposal.kind == "revised_study_plan":
        logger.info("audit event=external_write actor=%s outcome=not_configured proposal_id=%s", actor, proposal.id)
    logger.info("audit event=proposal_decision actor=%s outcome=%s proposal_id=%s", actor, proposal.status, proposal.id)
    return academic.proposal_data(proposal)


@app.get("/api/audit")
async def get_audit_history(request: Request, db: Session = Depends(get_db)) -> list[dict]:
    _authenticated_user(request)
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(50)).all()
    return [
        {"id": event.id, "actor": event.actor, "action": event.action, "entity_type": event.entity_type, "entity_id": event.entity_id, "created_at": event.created_at.isoformat()}
        for event in events
    ]


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    built_index = FRONTEND_ROOT / "dist" / "index.html"
    return FileResponse(built_index if built_index.is_file() else FRONTEND_ROOT / "index.html")


@app.get("/assets/{asset_path:path}", include_in_schema=False)
async def assets(asset_path: str) -> FileResponse:
    candidate = (FRONTEND_ROOT / "dist" / asset_path).resolve()
    if not candidate.is_relative_to(FRONTEND_ROOT.resolve()) or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(candidate)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.api_port, log_level="info")
