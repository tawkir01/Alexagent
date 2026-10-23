from __future__ import annotations

import logging
import time
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from backend import academic
from backend.db import SessionLocal

logger = logging.getLogger("campusflow.audit")


def _audit(tool: str, started: float, outcome: str) -> None:
    logger.info(
        "audit event=mcp_tool actor=mcp_client tool=%s outcome=%s duration_ms=%d",
        tool,
        outcome,
        round((time.perf_counter() - started) * 1000),
    )


def create_mcp_server() -> FastMCP:
    server = FastMCP("CampusFlow")

    @server.tool()
    def list_upcoming_deadlines() -> dict[str, Any]:
        """Return academic assignments with course details, estimated work, and due dates."""
        started = time.perf_counter()
        outcome = "error"
        try:
            with SessionLocal() as db:
                result = {"assignments": academic.list_assignments(db)}
                outcome = "success"
                return result
        finally:
            _audit("list_upcoming_deadlines", started, outcome)

    @server.tool()
    def detect_deadline_changes_and_conflicts() -> dict[str, Any]:
        """Compare current and historical source records to identify changed or conflicting deadlines."""
        started = time.perf_counter()
        outcome = "error"
        try:
            with SessionLocal() as db:
                result = {
                    "changes": academic.deadline_changes(db),
                    "conflicts": academic.deadline_conflicts(db),
                }
                outcome = "success"
                return result
        finally:
            _audit("detect_deadline_changes_and_conflicts", started, outcome)

    @server.tool()
    def get_academic_change_history() -> dict[str, Any]:
        """Return the complete academic change timeline with old/new values, statuses, and evidence IDs."""
        started = time.perf_counter()
        outcome = "error"
        try:
            with SessionLocal() as db:
                result = {
                    "history": academic.change_history(db),
                    "conflicts": academic.deadline_conflicts(db),
                }
                outcome = "success"
                return result
        finally:
            _audit("get_academic_change_history", started, outcome)

    @server.tool()
    def record_academic_update(
        record_key: Annotated[str, Field(min_length=3, max_length=100)],
        record_kind: Literal["deadline", "examination_date", "assignment_requirement", "notice"],
        record_value: Annotated[str, Field(min_length=1, max_length=2000)],
        source_id: Annotated[str, Field(min_length=2, max_length=40)],
        source_title: Annotated[str, Field(min_length=2, max_length=180)],
        source_type: Literal["lms", "email", "notice", "calendar"],
        content: Annotated[str, Field(min_length=2, max_length=10000)],
    ) -> dict[str, Any]:
        """Record a new version of a deadline, exam date, assignment requirement, or notice and compare it with history."""
        started = time.perf_counter()
        outcome = "error"
        try:
            with SessionLocal() as db:
                result = academic.ingest_academic_record(
                    db,
                    record_key=record_key,
                    record_kind=record_kind,
                    record_value=record_value,
                    source_id=source_id,
                    source_title=source_title,
                    source_type=source_type,
                    content=content,
                )
                outcome = "success"
                return result
        finally:
            _audit("record_academic_update", started, outcome)

    @server.tool()
    def publish_signature_demo_notice() -> dict[str, Any]:
        """Publish the reproducible synthetic October 30 DBMS notice to demonstrate evidence conflict detection."""
        started = time.perf_counter()
        outcome = "error"
        try:
            with SessionLocal() as db:
                result = academic.publish_demo_notice(db)
                outcome = "success"
                return result
        finally:
            _audit("publish_signature_demo_notice", started, outcome)

    @server.tool()
    def simulate_academic_workload(lost_hours_tomorrow: Annotated[float, Field(ge=0, le=16)] = 0) -> dict[str, Any]:
        """Deterministically simulate workload, schedule fit, and explainable risks for a lost-study-time scenario."""
        started = time.perf_counter()
        outcome = "error"
        try:
            with SessionLocal() as db:
                result = academic.simulate_workload(db, {"lost_hours_tomorrow": lost_hours_tomorrow})
                outcome = "success"
                return result
        finally:
            _audit("simulate_academic_workload", started, outcome)

    @server.tool()
    def propose_revised_study_plan(lost_hours_tomorrow: Annotated[float, Field(ge=0, le=16)] = 0) -> dict[str, Any]:
        """Create a pending study-plan proposal from the digital twin; no external calendar is changed."""
        started = time.perf_counter()
        outcome = "error"
        try:
            with SessionLocal() as db:
                proposal = academic.create_revised_plan(
                    db, "mcp_user", {"lost_hours_tomorrow": lost_hours_tomorrow}
                )
                result = academic.proposal_data(proposal)
                outcome = "success"
                return result
        finally:
            _audit("propose_revised_study_plan", started, outcome)

    @server.tool()
    def search_academic_sources(
        query: Annotated[str, Field(min_length=2, max_length=120)],
        limit: Annotated[int, Field(ge=1, le=10)] = 5,
    ) -> dict[str, Any]:
        """Search synthetic LMS, email, and notice records and return cited source IDs."""
        started = time.perf_counter()
        outcome = "error"
        try:
            with SessionLocal() as db:
                terms = [term.casefold() for term in query.split() if len(term) > 2]
                records = academic.list_sources(db)
                matches = [
                    record
                    for record in records
                    if any(term in (record["title"] + " " + record["content"]).casefold() for term in terms)
                ][:limit]
                result = {"query": query, "count": len(matches), "sources": matches}
                outcome = "success"
                return result
        finally:
            _audit("search_academic_sources", started, outcome)

    @server.tool()
    def propose_study_plan() -> dict[str, Any]:
        """Create a pending study-plan proposal; it never changes an external calendar."""
        started = time.perf_counter()
        outcome = "error"
        try:
            with SessionLocal() as db:
                proposal = academic.create_study_plan(db, "mcp_user")
                result = academic.proposal_data(proposal)
                outcome = "success"
                return result
        finally:
            _audit("propose_study_plan", started, outcome)

    return server
