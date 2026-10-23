from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, joinedload

from backend.db import Base, SessionLocal, engine
from backend.models import (
    ActionProposal,
    AcademicChange,
    Assignment,
    AuditEvent,
    Course,
    DeadlineEvidence,
    SourceRecord,
    TwinPreferences,
)

NOW = datetime(2026, 10, 23, 9, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=NOW.tzinfo)
    return value.astimezone(timezone.utc)


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(Course.id).limit(1)) is not None:
            return
        seed_demo_data(db)


def seed_demo_data(db: Session) -> None:
    courses = [
        Course(id=1, code="CS301", name="Data Structures & Algorithms", instructor="Dr. Meera Shah", color="violet"),
        Course(id=2, code="CS315", name="Database Management Systems", instructor="Prof. Arjun Rao", color="blue"),
        Course(id=3, code="CS322", name="Operating Systems", instructor="Dr. Neha Iyer", color="amber"),
        Course(id=4, code="MA201", name="Discrete Mathematics", instructor="Prof. K. Menon", color="green"),
    ]
    db.add_all(courses)
    db.flush()
    assignments = [
        Assignment(id=1, course_id=1, title="Graph algorithms problem set", description="Implement and analyze shortest-path and minimum-spanning-tree algorithms.", due_at=datetime(2026, 10, 25, 23, 59, tzinfo=NOW.tzinfo), status="upcoming", estimated_hours=4, importance=4, updated_at=NOW - timedelta(days=3)),
        Assignment(id=2, course_id=2, title="Normalization & SQL lab", description="Submit the normalized schema and query report.", due_at=datetime(2026, 10, 28, 23, 59, tzinfo=NOW.tzinfo), status="upcoming", estimated_hours=3, importance=None, updated_at=NOW - timedelta(days=1)),
        Assignment(id=3, course_id=3, title="Process scheduling quiz", description="Review scheduling policies and complete the online quiz.", due_at=datetime(2026, 10, 30, 17, 0, tzinfo=NOW.tzinfo), status="upcoming", estimated_hours=2, importance=3, updated_at=NOW - timedelta(days=2)),
        Assignment(id=4, course_id=4, title="Proof techniques worksheet", description="Practice induction, contradiction, and set identities.", due_at=datetime(2026, 11, 2, 23, 59, tzinfo=NOW.tzinfo), status="upcoming", estimated_hours=3, importance=None, updated_at=NOW - timedelta(days=2)),
    ]
    sources = [
        SourceRecord(id=1, source_id="LMS-CS301-104", title="CS301 LMS assignment", source_type="lms", content="Graph algorithms problem set is due October 25 at 11:59 PM. The deadline was moved from October 24.", published_at=NOW - timedelta(hours=20), record_key="assignment:1:deadline", record_kind="deadline", record_value="2026-10-25T23:59:00+05:30"),
        SourceRecord(id=2, source_id="LMS-CS315-210", title="DBMS LMS assignment", source_type="lms", content="Normalization & SQL lab deadline: October 28 at 11:59 PM.", published_at=NOW - timedelta(days=1), record_key="assignment:2:deadline", record_kind="deadline", record_value="2026-10-28T23:59:00+05:30"),
        SourceRecord(id=4, source_id="LMS-CS322-304", title="Operating systems quiz", source_type="lms", content="Process scheduling quiz closes October 30 at 5:00 PM.", published_at=NOW - timedelta(days=2), record_key="assignment:3:deadline", record_kind="deadline", record_value="2026-10-30T17:00:00+05:30"),
        SourceRecord(id=5, source_id="NOTICE-CAMPUS-77", title="Midterm week room update", source_type="notice", content="CS301 midterm is scheduled for November 6 in Engineering Hall 204. Bring your student ID.", published_at=NOW - timedelta(hours=15), record_key="exam:CS301:midterm", record_kind="examination_date", record_value="2026-11-06"),
        SourceRecord(id=6, source_id="EMAIL-CS301-32", title="CS301 deadline update", source_type="email", content="The Graph algorithms problem set deadline was extended from October 24 to October 25 at 11:59 PM.", published_at=NOW - timedelta(hours=19), record_key="assignment:1:deadline", record_kind="deadline", record_value="2026-10-25T23:59:00+05:30"),
        SourceRecord(id=7, source_id="LMS-MA201-08", title="Discrete mathematics worksheet", source_type="lms", content="Proof techniques worksheet due November 2 at 11:59 PM.", published_at=NOW - timedelta(days=2), record_key="assignment:4:deadline", record_kind="deadline", record_value="2026-11-02T23:59:00+05:30"),
        SourceRecord(id=8, source_id="LMS-CS315-REQ-210", title="DBMS lab requirements", source_type="lms", content="Submit the normalized schema and query report.", published_at=NOW - timedelta(days=1), record_key="assignment:2:requirements", record_kind="assignment_requirement", record_value="Normalized schema and query report"),
        SourceRecord(id=9, source_id="NOTICE-SEMESTER-01", title="Academic calendar notice", source_type="notice", content="Campus closed on October 31.", published_at=NOW - timedelta(days=2), record_key="notice:semester-calendar", record_kind="notice", record_value="Campus closed on October 31"),
    ]
    db.add_all(assignments + sources)
    db.flush()
    evidence = [
        DeadlineEvidence(assignment_id=1, source_id=1, due_at=datetime(2026, 10, 25, 23, 59, tzinfo=NOW.tzinfo), recorded_at=NOW - timedelta(hours=20), current=True),
        DeadlineEvidence(assignment_id=1, source_id=1, due_at=datetime(2026, 10, 24, 23, 59, tzinfo=NOW.tzinfo), recorded_at=NOW - timedelta(days=3), current=False),
        DeadlineEvidence(assignment_id=1, source_id=6, due_at=datetime(2026, 10, 25, 23, 59, tzinfo=NOW.tzinfo), recorded_at=NOW - timedelta(hours=19), current=True),
        DeadlineEvidence(assignment_id=2, source_id=2, due_at=datetime(2026, 10, 28, 23, 59, tzinfo=NOW.tzinfo), recorded_at=NOW - timedelta(days=1), current=True),
        DeadlineEvidence(assignment_id=3, source_id=4, due_at=datetime(2026, 10, 30, 17, 0, tzinfo=NOW.tzinfo), recorded_at=NOW - timedelta(days=2), current=True),
        DeadlineEvidence(assignment_id=4, source_id=7, due_at=datetime(2026, 11, 2, 23, 59, tzinfo=NOW.tzinfo), recorded_at=NOW - timedelta(days=2), current=True),
    ]
    db.add_all(evidence)
    db.add(AcademicChange(
        entity_type="assignment",
        entity_id="1",
        entity_title="Graph algorithms problem set",
        field_name="due_at",
        old_value=datetime(2026, 10, 24, 23, 59, tzinfo=NOW.tzinfo).isoformat(),
        new_value=datetime(2026, 10, 25, 23, 59, tzinfo=NOW.tzinfo).isoformat(),
        source_id="LMS-CS301-104",
        detected_at=NOW - timedelta(hours=19),
        status="verified",
        evidence_ids=["LMS-CS301-104", "EMAIL-CS301-32"],
    ))
    availability = {
        (NOW.date() + timedelta(days=offset)).isoformat(): (3.0 if (NOW.date() + timedelta(days=offset)).weekday() < 5 else 4.0)
        for offset in range(15)
    }
    db.add(TwinPreferences(
        id=1,
        availability=availability,
        session_minutes=60,
        planned_sessions=[{
            "id": "study-cs301-2026-10-23",
            "assignment_id": 1,
            "date": "2026-10-23",
            "minutes": 90,
        }],
        importance={},
        updated_at=NOW,
    ))
    db.commit()


def assignment_data(item: Assignment) -> dict[str, Any]:
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "due_at": item.due_at.isoformat(),
        "status": item.status,
        "estimated_hours": item.estimated_hours,
        "importance": item.importance,
        "course": {"code": item.course.code, "name": item.course.name, "color": item.course.color},
        "updated_at": item.updated_at.isoformat(),
    }


def list_assignments(db: Session) -> list[dict[str, Any]]:
    items = db.scalars(
        select(Assignment).options(joinedload(Assignment.course)).order_by(Assignment.due_at)
    ).unique().all()
    return [assignment_data(item) for item in items]


def list_sources(db: Session) -> list[dict[str, Any]]:
    return [
        {
            "source_id": source.source_id,
            "title": source.title,
            "type": source.source_type,
            "content": source.content,
            "published_at": _utc_datetime(source.published_at).isoformat(),
            "verified": source.verified,
            "record_key": source.record_key,
            "record_kind": source.record_kind,
            "record_value": source.record_value,
        }
        for source in db.scalars(select(SourceRecord).order_by(SourceRecord.published_at.desc())).all()
    ]


def ingest_academic_record(
    db: Session,
    *,
    record_key: str,
    record_kind: str,
    record_value: str,
    source_id: str,
    source_title: str,
    source_type: str,
    content: str,
    published_at: datetime | None = None,
) -> dict[str, Any]:
    if db.scalar(select(SourceRecord.id).where(SourceRecord.source_id == source_id)) is not None:
        raise ValueError(f"Source ID {source_id} already exists")

    previous = db.scalar(
        select(SourceRecord)
        .where(SourceRecord.record_key == record_key)
        .order_by(SourceRecord.published_at.desc(), SourceRecord.id.desc())
        .limit(1)
    )
    previous_in_source = db.scalar(
        select(SourceRecord)
        .where(SourceRecord.record_key == record_key, SourceRecord.source_type == source_type)
        .order_by(SourceRecord.published_at.desc(), SourceRecord.id.desc())
        .limit(1)
    )
    recorded_at = published_at or NOW
    if previous_in_source and _utc_datetime(recorded_at) < _utc_datetime(previous_in_source.published_at):
        raise ValueError("The source timestamp predates its latest recorded version")

    assignment_id = None
    entity_type = record_kind
    field_name = record_kind
    entity_title = source_title
    key_parts = record_key.split(":")
    if len(key_parts) == 3 and key_parts[0] == "assignment" and key_parts[1].isdigit():
        assignment_id = int(key_parts[1])
        assignment = db.scalar(
            select(Assignment).options(joinedload(Assignment.course)).where(Assignment.id == assignment_id)
        )
        if assignment is None:
            raise ValueError(f"Academic record references unknown assignment {assignment_id}")
        entity_type = "assignment"
        entity_title = assignment.title
        field_name = "due_at" if record_kind == "deadline" else record_kind
    elif record_kind == "examination_date":
        entity_type = "examination"

    due_at = None
    if record_kind == "deadline":
        try:
            due_at = datetime.fromisoformat(record_value)
        except ValueError:
            due_at = datetime.combine(date.fromisoformat(record_value), datetime.min.time(), tzinfo=NOW.tzinfo)

    source = SourceRecord(
        source_id=source_id,
        title=source_title,
        source_type=source_type,
        content=content,
        published_at=recorded_at,
        verified=True,
        record_key=record_key,
        record_kind=record_kind,
        record_value=record_value,
    )
    db.add(source)
    db.flush()

    version_rows = db.scalars(
        select(SourceRecord)
        .where(SourceRecord.record_key == record_key)
        .order_by(SourceRecord.published_at.desc(), SourceRecord.id.desc())
    ).all()
    latest_by_source_type: dict[str, SourceRecord] = {}
    for row in version_rows:
        latest_by_source_type.setdefault(row.source_type, row)
    current_values = {row.record_value for row in latest_by_source_type.values()}
    evidence_ids = [
        row.source_id for row in latest_by_source_type.values()
        if len(current_values) > 1 or row.record_value == record_value
    ]
    status_value = (
        "disputed" if len(current_values) > 1
        else "verified" if len(latest_by_source_type) >= 2
        else "awaiting_confirmation"
    )

    if record_kind == "deadline" and assignment_id is not None and due_at is not None:
        if previous_in_source:
            db.execute(update(DeadlineEvidence).where(
                DeadlineEvidence.source_id == previous_in_source.id,
                DeadlineEvidence.current.is_(True),
            ).values(current=False))
        db.add(DeadlineEvidence(
            assignment_id=assignment_id,
            source_id=source.id,
            due_at=due_at,
            recorded_at=recorded_at,
            current=True,
        ))
        db.flush()
        if any(item["assignment_id"] == assignment_id for item in deadline_conflicts(db)):
            status_value = "disputed"
    for row in latest_by_source_type.values():
        row.verified = status_value == "verified" and row.record_value == record_value

    comparison_source = previous_in_source or previous
    changed = comparison_source is None or comparison_source.record_value != record_value
    event_data = None
    if changed:
        old_value = comparison_source.record_value if comparison_source and comparison_source.record_value is not None else "No prior version available"
        event = AcademicChange(
            entity_type=entity_type,
            entity_id=str(assignment_id) if assignment_id is not None else record_key,
            entity_title=entity_title,
            field_name=field_name,
            old_value=old_value,
            new_value=record_value,
            source_id=source_id,
            detected_at=recorded_at,
            status=status_value,
            evidence_ids=evidence_ids,
        )
        db.add(event)
        db.flush()
        event_data = next(item for item in change_history(db) if item["id"] == event.id)
    else:
        prior_event = db.scalar(
            select(AcademicChange)
            .join(SourceRecord, SourceRecord.source_id == AcademicChange.source_id)
            .where(SourceRecord.record_key == record_key)
            .order_by(AcademicChange.detected_at.desc(), AcademicChange.id.desc())
            .limit(1)
        )
        if prior_event:
            prior_event.status = status_value
            prior_event.evidence_ids = evidence_ids
            db.flush()
            event_data = next(item for item in change_history(db) if item["id"] == prior_event.id)

    db.add(AuditEvent(
        actor="academic_record_ingest",
        action="academic_record_ingested",
        entity_type=record_kind,
        entity_id=record_key,
        details={"source_id": source_id, "changed": changed},
        created_at=recorded_at,
    ))
    db.commit()
    return {
        "created": True,
        "changed": changed,
        "source": next(item for item in list_sources(db) if item["source_id"] == source_id),
        "change": event_data,
    }


def deadline_changes(db: Session) -> list[dict[str, Any]]:
    return change_history(db)


def deadline_conflicts(db: Session) -> list[dict[str, Any]]:
    evidence = db.scalars(
        select(DeadlineEvidence)
        .where(DeadlineEvidence.current.is_(True))
        .options(joinedload(DeadlineEvidence.assignment).joinedload(Assignment.course), joinedload(DeadlineEvidence.source))
    ).unique().all()
    grouped: dict[int, list[DeadlineEvidence]] = {}
    for item in evidence:
        grouped.setdefault(item.assignment_id, []).append(item)
    conflicts = []
    for records in grouped.values():
        due_values = {
            _utc_datetime(item.due_at).replace(second=0, microsecond=0)
            for item in records
        }
        if len(due_values) < 2:
            continue
        first = records[0]
        conflicts.append({
            "assignment_id": first.assignment.id,
            "assignment": first.assignment.title,
            "course": first.assignment.course.code,
            "status": "conflicting",
            "message": "Sources currently list different due dates. Confirm with the instructor before relying on either date.",
            "sources": [{
                "source_id": item.source.source_id,
                "source_title": item.source.title,
                "due_at": item.due_at.isoformat(),
                "published_at": _utc_datetime(item.source.published_at).isoformat(),
            } for item in sorted(records, key=lambda item: _utc_datetime(item.source.published_at), reverse=True)],
        })
    return conflicts


def change_history(db: Session) -> list[dict[str, Any]]:
    events = db.scalars(select(AcademicChange).order_by(AcademicChange.detected_at.desc(), AcademicChange.id.desc())).all()
    course_codes = {item["id"]: item["course"]["code"] for item in list_assignments(db)}
    return [
        {
            "id": event.id,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "assignment_id": int(event.entity_id) if event.entity_type == "assignment" and event.entity_id.isdigit() else None,
            "assignment": event.entity_title,
            "course": course_codes.get(int(event.entity_id)) if event.entity_type == "assignment" and event.entity_id.isdigit() else None,
            "field": event.field_name,
            "old_value": event.old_value,
            "new_value": event.new_value,
            "old_due_at": event.old_value,
            "new_due_at": event.new_value,
            "source_id": event.source_id,
            "detected_at": _utc_datetime(event.detected_at).isoformat(),
            "status": event.status,
            "evidence_ids": event.evidence_ids,
        }
        for event in events
    ]


def publish_demo_notice(db: Session) -> dict[str, Any]:
    existing = db.scalar(select(SourceRecord).where(SourceRecord.source_id == "NOTICE-CS315-18"))
    if existing:
        return {"created": False, "source_id": existing.source_id, "history": change_history(db)}

    source = SourceRecord(
        source_id="NOTICE-CS315-18",
        title="Updated DBMS lab schedule",
        source_type="notice",
        content="The department notice lists the Normalization & SQL lab due date as October 30 at 11:59 PM. Please verify the discrepancy before relying on either date.",
        published_at=NOW - timedelta(hours=1),
        record_key="assignment:2:deadline",
        record_kind="deadline",
        record_value="2026-10-30T23:59:00+05:30",
    )
    db.add(source)
    db.flush()
    lms_evidence = db.scalar(
        select(DeadlineEvidence)
        .where(DeadlineEvidence.assignment_id == 2, DeadlineEvidence.current.is_(True))
        .order_by(DeadlineEvidence.recorded_at.desc())
    )
    if lms_evidence is None:
        raise ValueError("The demo DBMS LMS deadline evidence is missing")
    new_deadline = datetime(2026, 10, 30, 23, 59, tzinfo=NOW.tzinfo)
    db.add(DeadlineEvidence(
        assignment_id=2,
        source_id=source.id,
        due_at=new_deadline,
        recorded_at=NOW,
        current=True,
    ))
    db.add(AcademicChange(
        entity_type="assignment",
        entity_id="2",
        entity_title="Normalization & SQL lab",
        field_name="due_at",
        old_value=lms_evidence.due_at.isoformat(),
        new_value=new_deadline.isoformat(),
        source_id=source.source_id,
        detected_at=NOW,
        status="disputed",
        evidence_ids=["LMS-CS315-210", source.source_id],
    ))
    db.add(AuditEvent(
        actor="demo",
        action="demo_notice_published",
        entity_type="assignment",
        entity_id="2",
        details={"source_id": source.source_id, "status": "disputed"},
        created_at=NOW,
    ))
    db.commit()
    return {"created": True, "source_id": source.source_id, "history": change_history(db)}


def reset_demo_data(db: Session) -> None:
    for model in (AuditEvent, ActionProposal, AcademicChange, TwinPreferences, DeadlineEvidence, SourceRecord, Assignment, Course):
        db.execute(delete(model))
    db.commit()
    seed_demo_data(db)


def _preferences(db: Session) -> TwinPreferences:
    preferences = db.get(TwinPreferences, 1)
    if preferences:
        return preferences
    availability = {
        (NOW.date() + timedelta(days=offset)).isoformat(): (3.0 if (NOW.date() + timedelta(days=offset)).weekday() < 5 else 4.0)
        for offset in range(15)
    }
    preferences = TwinPreferences(
        id=1,
        availability=availability,
        session_minutes=60,
        planned_sessions=[],
        importance={},
        updated_at=NOW,
    )
    db.add(preferences)
    db.commit()
    db.refresh(preferences)
    return preferences


def twin_preferences_data(db: Session) -> dict[str, Any]:
    prefs = _preferences(db)
    return {
        "availability": prefs.availability,
        "session_minutes": prefs.session_minutes,
        "planned_sessions": prefs.planned_sessions,
        "importance": prefs.importance,
    }


def update_twin_preferences(
    db: Session,
    availability: dict[str, float],
    session_minutes: int,
    importance: dict[str, int] | None = None,
) -> dict[str, Any]:
    prefs = _preferences(db)
    prefs.availability = availability
    prefs.session_minutes = session_minutes
    if importance is not None:
        prefs.importance = importance
    prefs.updated_at = datetime.now(timezone.utc)
    db.commit()
    return twin_preferences_data(db)


def simulate_workload(db: Session, scenario: dict[str, Any] | None = None) -> dict[str, Any]:
    scenario = scenario or {}
    prefs = _preferences(db)
    assignments = list_assignments(db)
    availability = dict(prefs.availability)
    tomorrow = (NOW.date() + timedelta(days=1)).isoformat()
    lost_hours = float(scenario.get("lost_hours_tomorrow", 0))
    availability[tomorrow] = max(0.0, float(availability.get(tomorrow, 0)) - lost_hours)
    planned_sessions = [dict(session) for session in prefs.planned_sessions]
    move = scenario.get("move_session")
    if move:
        session = next((item for item in planned_sessions if item["id"] == move["session_id"]), None)
        if session is None:
            raise ValueError("The selected planned study session was not found")
        session["date"] = move["to_date"]

    extra_assignment = scenario.get("increase_estimate")
    if extra_assignment:
        target = next((item for item in assignments if item["id"] == extra_assignment["assignment_id"]), None)
        if target is None:
            raise ValueError("The selected assignment was not found")
        target["estimated_hours"] += float(extra_assignment["extra_hours"])

    assignments_by_id = {item["id"]: item for item in assignments}
    extra = scenario.get("additional_assignment")
    if extra:
        assignments.append({
            "id": -1,
            "title": extra["title"],
            "description": "Scenario-only task; it is not saved to the academic record.",
            "due_at": datetime.combine(
                date.fromisoformat(extra["due_date"]) if isinstance(extra["due_date"], str) else extra["due_date"],
                datetime.min.time(),
                tzinfo=NOW.tzinfo,
            ).isoformat(),
            "estimated_hours": float(extra["estimated_hours"]),
            "importance": extra.get("importance"),
            "course": {"code": extra.get("course_code", "EXTRA"), "name": "Scenario task", "color": "amber"},
        })
    else:
        extra = None

    conflicts = {item["assignment_id"]: item for item in deadline_conflicts(db)}
    for assignment_id, conflict in conflicts.items():
        assignment = assignments_by_id.get(assignment_id)
        if not assignment:
            continue
        possible_dates = [datetime.fromisoformat(item["due_at"]).date() for item in conflict["sources"]]
        assignment["planning_due"] = min(possible_dates).isoformat()
        assignment["deadline_uncertainty"] = {
            "status": "disputed",
            "window_start": min(possible_dates).isoformat(),
            "window_end": max(possible_dates).isoformat(),
            "source_ids": [item["source_id"] for item in conflict["sources"]],
            "explanation": "Dates disagree across current sources. The earlier date is used only as a conservative planning boundary, not treated as confirmed.",
        }
    for assignment in assignments:
        assignment.setdefault("planning_due", datetime.fromisoformat(assignment["due_at"]).date().isoformat())
        assignment.setdefault("deadline_uncertainty", {"status": "none", "source_ids": [], "explanation": "No conflicting deadline source found."})

    planned_minutes: dict[int, int] = {}
    scheduled_by_day: dict[str, list[dict[str, Any]]] = {}
    reserved_by_day: dict[str, float] = {}
    for session in planned_sessions:
        assignment = assignments_by_id.get(session["assignment_id"])
        if not assignment:
            continue
        planned_minutes[session["assignment_id"]] = planned_minutes.get(session["assignment_id"], 0) + int(session["minutes"])
        reserved_by_day[session["date"]] = reserved_by_day.get(session["date"], 0.0) + int(session["minutes"]) / 60
        scheduled_by_day.setdefault(session["date"], []).append({
            "assignment_id": session["assignment_id"],
            "assignment": assignment["title"],
            "course": assignment["course"]["code"],
            "minutes": int(session["minutes"]),
            "existing": True,
        })

    remaining = {
        item["id"]: max(0.0, float(item["estimated_hours"]) - planned_minutes.get(item["id"], 0) / 60)
        for item in assignments
    }
    effective_due = {item["id"]: date.fromisoformat(item["planning_due"]) for item in assignments}
    start_date = NOW.date()
    end_date = max(effective_due.values(), default=start_date)
    capacity_by_day: dict[str, float] = {}
    schedule: list[dict[str, Any]] = []
    day = start_date
    while day <= end_date:
        key = day.isoformat()
        capacity = max(0.0, float(availability.get(key, 0)) - reserved_by_day.get(key, 0))
        capacity_by_day[key] = capacity
        slots = list(scheduled_by_day.get(key, []))
        for assignment in sorted(assignments, key=lambda item: (effective_due[item["id"]], item["title"])):
            if day > effective_due[assignment["id"]] or remaining[assignment["id"]] <= 0 or capacity <= 0:
                continue
            hours = min(remaining[assignment["id"]], capacity, prefs.session_minutes / 60)
            minutes = int(round(hours * 60))
            slots.append({
                "assignment_id": assignment["id"],
                "assignment": assignment["title"],
                "course": assignment["course"]["code"],
                "minutes": minutes,
                "existing": False,
            })
            remaining[assignment["id"]] = max(0.0, remaining[assignment["id"]] - minutes / 60)
            capacity = max(0.0, capacity - minutes / 60)
        if slots:
            schedule.append({"date": key, "available_hours": availability.get(key, 0), "sessions": slots})
        day += timedelta(days=1)

    risks = []
    today = NOW.date()
    remaining_work_hours = sum(remaining.values())
    for item in sorted(assignments, key=lambda task: (effective_due[task["id"]], task["title"])):
        due = effective_due[item["id"]]
        days_left = max(0, (due - today).days)
        already_planned = planned_minutes.get(item["id"], 0) / 60
        hours_remaining = max(0.0, float(item["estimated_hours"]) - already_planned)
        available_hours = sum(
            max(0.0, float(value) - reserved_by_day.get(day_key, 0))
            for day_key, value in availability.items()
            if today <= date.fromisoformat(day_key) <= due
        )
        workload_ratio = hours_remaining / max(available_hours, 0.5)
        urgency_points = 24 if days_left <= 2 else 16 if days_left <= 5 else 8 if days_left <= 10 else 0
        workload_points = min(60, round(workload_ratio * 35))
        importance = int(prefs.importance.get(str(item["id"]), item.get("importance") or 3))
        importance_points = max(0, (importance - 3) * 4) if str(item["id"]) in prefs.importance or item.get("importance") is not None else 0
        uncertainty_points = 12 if item["deadline_uncertainty"]["status"] == "disputed" else 0
        score = min(100, workload_points + urgency_points + importance_points + uncertainty_points)
        status = "At risk" if score >= 70 else "Needs attention" if score >= 40 else "On track"
        reasons = [
            f"{hours_remaining:g} estimated work hours remain after {already_planned:g} planned hours.",
            f"{available_hours:g} available study hours fall before the conservative planning date ({due.isoformat()}).",
            f"Deadline urgency contributes {urgency_points} points at {days_left} days remaining.",
        ]
        if importance_points:
            reasons.append(f"Student-provided importance ({importance}/5) contributes {importance_points} points.")
        if uncertainty_points:
            reasons.append("A disputed deadline adds 12 caution points; its uncertainty is shown separately.")
        risks.append({
            "assignment_id": item["id"],
            "assignment": item["title"],
            "course": item["course"]["code"],
            "due_at": item["due_at"],
            "planning_due": due.isoformat(),
            "days_remaining": days_left,
            "estimated_hours_remaining": round(hours_remaining, 2),
            "available_hours_before_due": round(available_hours, 2),
            "workload_score": min(100, workload_points + urgency_points + importance_points),
            "uncertainty_points": uncertainty_points,
            "priority_score": score,
            "status": status,
            "importance": importance if str(item["id"]) in prefs.importance or item.get("importance") is not None else None,
            "deadline_uncertainty": item["deadline_uncertainty"],
            "explanation": " ".join(reasons),
        })

    missed = [
        {"assignment_id": item["id"], "assignment": item["title"], "unscheduled_hours": round(remaining[item["id"]], 2), "due_at": item["planning_due"]}
        for item in assignments if remaining[item["id"]] > 0
    ]
    total_capacity = sum(capacity_by_day.values())
    alternatives = []
    if missed:
        alternatives.append(f"{sum(item['unscheduled_hours'] for item in missed):g} study hours do not fit before the planning boundaries; add availability earlier or reduce optional work.")
        alternatives.append("Start with the earliest deadline, then use one shorter review block for each lower-urgency task.")
    else:
        alternatives.append("The listed workload fits the provided availability; keep the existing sessions and protect the earliest-deadline blocks.")
    assumptions = [
        "Availability is the student-provided number of focused hours per date; unspecified dates have zero capacity.",
        f"Sessions are capped at the preferred {prefs.session_minutes}-minute duration. No breaks or task-switching overhead are modeled.",
        "Existing planned sessions reserve capacity and count toward that assignment's estimated effort.",
        "The deterministic scheduler fills earliest conservative deadlines first; it does not predict grades or guarantee outcomes.",
    ]
    if lost_hours:
        assumptions.append(f"The scenario removes {lost_hours:g} available hours from {tomorrow}.")
    if extra:
        assumptions.append(f"'{extra['title']}' exists only in this simulation and was not saved to the academic record.")
    if move:
        assumptions.append(f"Session {move['session_id']} was moved to {move['to_date']} for this simulation only.")
    return {
        "scenario": scenario,
        "schedule": schedule,
        "risks": risks,
        "unscheduled": missed,
        "summary": {
            "task_count": len(assignments),
            "remaining_work_hours": round(remaining_work_hours, 2),
            "available_capacity_hours": round(total_capacity, 2),
            "fits": not missed,
        },
        "assumptions": assumptions,
        "alternatives": alternatives,
        "planned_sessions": planned_sessions,
        "preferences": twin_preferences_data(db),
    }


def create_revised_plan(db: Session, actor: str, scenario: dict[str, Any]) -> ActionProposal:
    simulation = simulate_workload(db, scenario)
    proposal = ActionProposal(
        kind="revised_study_plan",
        title="Revised study plan from workload simulation",
        payload={
            "notice": "Review required. Approval records your choice only; no external calendar is connected or modified.",
            "schedule": simulation["schedule"],
            "risks": simulation["risks"],
            "unscheduled": simulation["unscheduled"],
            "assumptions": simulation["assumptions"],
            "alternatives": simulation["alternatives"],
            "scenario": simulation["scenario"],
            "outcome": "pending_student_review",
        },
        status="pending",
        created_at=datetime.now(timezone.utc),
        actor=actor,
    )
    db.add(proposal)
    db.flush()
    db.add(AuditEvent(
        actor=actor,
        action="revised_plan_proposed",
        entity_type="study_plan",
        entity_id=str(proposal.id),
        details={"scenario": simulation["scenario"], "status": "pending"},
        created_at=datetime.now(timezone.utc),
    ))
    db.commit()
    db.refresh(proposal)
    return proposal


def dashboard(db: Session) -> dict[str, Any]:
    assignments = list_assignments(db)
    open_assignments = [item for item in assignments if item["status"] != "completed"]
    courses = db.scalars(select(Course).order_by(Course.code)).all()
    sources = list_sources(db)
    return {
        "student": {"name": "Alex Morgan", "program": "Computer Engineering · Year 3"},
        "stats": {
            "courses": len(courses),
            "upcoming": len(open_assignments),
            "changes": len(deadline_changes(db)),
            "conflicts": len(deadline_conflicts(db)),
        },
        "courses": [{"code": c.code, "name": c.name, "color": c.color} for c in courses],
        "assignments": open_assignments,
        "changes": deadline_changes(db),
        "conflicts": deadline_conflicts(db),
        "demo_notice_published": any(source["source_id"] == "NOTICE-CS315-18" for source in sources),
        "notices": [s for s in sources if s["type"] == "notice"],
        "integrations": {"lms": "demo", "email": "optional_not_connected", "calendar": "optional_not_connected"},
    }


def ask_academic_question(prompt: str, db: Session) -> dict[str, Any]:
    normalized = prompt.casefold()
    words = {word.strip(".,?!:;") for word in normalized.split()}
    assignments = list_assignments(db)
    sources = list_sources(db)
    conflicts = deadline_conflicts(db)
    changes = deadline_changes(db)
    matched = [
        source for source in sources
        if any(len(word) > 3 and word in (source["title"] + " " + source["content"]).casefold() for word in words)
    ]
    if "conflict" in normalized or "contradict" in normalized or "disagree" in normalized:
        answer = (
            "I found a deadline conflict in your academic sources. The DBMS lab is listed as October 28 in the LMS and October 30 in a department notice. This is unresolved; check with the instructor before relying on either date."
            if conflicts
            else "I don't see an unresolved deadline conflict in the current sources. Run the reproducible Change Radar scenario to inspect a newly published notice."
        )
        facts = []
        assumptions = ["The sources may refer to different submission windows; that is not confirmed."]
        recommendations = ["Ask the DBMS instructor which deadline is authoritative."]
    elif "change" in normalized or "changed" in normalized or "update" in normalized:
        answer = "Your Graph algorithms problem set deadline moved from October 24 to October 25 at 11:59 PM. The LMS update and course email agree on the new date."
        facts = [{"claim": "Graph algorithms problem set deadline changed from Oct 24 to Oct 25 at 11:59 PM.", "source_ids": ["LMS-CS301-104", "EMAIL-CS301-32"]}]
        assumptions = []
        recommendations = ["Prioritize the DBMS lab conflict check; its due date is not verified."]
    elif "study" in normalized or "plan" in normalized or "prepare" in normalized:
        answer = "You have four upcoming assignments. Start with Graph algorithms (4 hours, due Oct 25), then split the DBMS lab (3 hours) and scheduling quiz (2 hours) into focused sessions. The DBMS deadline is conflicting across sources, so verify it."
        facts = [{"claim": f"{item['title']} is due {item['due_at']}.", "source_ids": [s["source_id"] for s in sources if item["title"].split()[0].casefold() in (s["title"] + " " + s["content"]).casefold()]} for item in assignments[:3]]
        assumptions = ["Study blocks are suggestions based on estimated effort, not your calendar availability."]
        recommendations = ["Block two 90-minute sessions for Graph algorithms today and tomorrow.", "Confirm the DBMS lab deadline with your instructor."]
    else:
        if conflicts:
            answer = "Here’s your current academic snapshot: Graph algorithms is due Oct 25, the DBMS lab has conflicting Oct 28 and Oct 30 source dates, and the scheduling quiz is due Oct 30. Verify the DBMS date with your instructor."
            facts = [{"claim": "The LMS lists the DBMS lab due Oct 28; a department notice lists Oct 30.", "source_ids": ["LMS-CS315-210", "NOTICE-CS315-18"]}]
            recommendations = ["Confirm the DBMS lab due date before scheduling work around it."]
        else:
            answer = "The DBMS lab is currently listed as due October 28 in the LMS. No newer conflicting notice has been published in this demo yet."
            facts = [{"claim": "The DBMS lab LMS record lists October 28 at 11:59 PM.", "source_ids": ["LMS-CS315-210"]}]
            recommendations = ["Check Change Radar for updates."]
        assumptions = ["I’m using the sample semester data provided in this demo."]
    return {
        "answer": answer,
        "mode": "deterministic_demo",
        "verified_facts": facts,
        "conflicts": conflicts if "conflict" in normalized or "contradict" in normalized or "disagree" in normalized else conflicts,
        "assumptions": assumptions,
        "recommendations": recommendations,
        "sources": matched[:5] or sources[:3],
        "changes": changes,
        "generated_at": NOW.isoformat(),
    }


def create_study_plan(db: Session, actor: str) -> ActionProposal:
    assignments = [item for item in list_assignments(db) if item["status"] != "completed"][:3]
    proposal = ActionProposal(
        kind="study_plan",
        title="Study plan for your next deadlines",
        payload={
            "notice": "Suggested schedule only; this does not modify your calendar.",
            "sessions": [
                {"day": index + 1, "assignment": item["title"], "course": item["course"]["code"], "due_at": item["due_at"], "minutes": min(item["estimated_hours"] * 30, 120), "focus": item["description"]}
                for index, item in enumerate(assignments)
            ],
        },
        status="pending",
        created_at=datetime.now(timezone.utc),
        actor=actor,
    )
    db.add(proposal)
    db.flush()
    db.add(AuditEvent(actor=actor, action="proposal_created", entity_type="study_plan", entity_id=str(proposal.id), details={"kind": proposal.kind}, created_at=datetime.now(timezone.utc)))
    db.commit()
    db.refresh(proposal)
    return proposal


def decide_proposal(db: Session, proposal: ActionProposal, actor: str, approved: bool) -> None:
    proposal.status = "approved" if approved else "rejected"
    proposal.decided_at = datetime.now(timezone.utc)
    outcome = "approved_no_external_calendar_write" if approved else "declined_no_external_calendar_write"
    if proposal.kind == "revised_study_plan":
        proposal.payload = {**proposal.payload, "outcome": outcome}
    db.add(AuditEvent(
        actor=actor,
        action=proposal.status,
        entity_type=proposal.kind,
        entity_id=str(proposal.id),
        details={"status": proposal.status, "outcome": outcome},
        created_at=proposal.decided_at,
    ))
    db.commit()


def proposal_data(proposal: ActionProposal) -> dict[str, Any]:
    return {
        "id": proposal.id,
        "kind": proposal.kind,
        "title": proposal.title,
        "payload": proposal.payload,
        "status": proposal.status,
        "created_at": proposal.created_at.isoformat(),
    }
