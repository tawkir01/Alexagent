from backend import academic
from backend.db import SessionLocal


def test_deadline_change_and_source_conflict_are_distinguished():
    with SessionLocal() as db:
        assert academic.list_assignments(db)[1]["due_at"].startswith("2026-10-28")
        changes = academic.deadline_changes(db)
        conflicts = academic.deadline_conflicts(db)
    assert len(changes) == 1
    assert changes[0]["status"] == "verified"
    assert changes[0]["old_due_at"].startswith("2026-10-24")
    assert changes[0]["new_due_at"].startswith("2026-10-25")
    assert conflicts == []

    with SessionLocal() as db:
        outcome = academic.publish_demo_notice(db)
        conflicts = academic.deadline_conflicts(db)
        history = academic.change_history(db)
        assignment = academic.list_assignments(db)[1]
    assert outcome["created"] is True
    assert assignment["due_at"].startswith("2026-10-28")
    assert len(conflicts) == 1
    assert conflicts[0]["status"] == "conflicting"
    assert {source["source_id"] for source in conflicts[0]["sources"]} == {
        "LMS-CS315-210",
        "NOTICE-CS315-18",
    }
    disputed = next(event for event in history if event["assignment_id"] == 2)
    assert disputed["status"] == "disputed"
    assert disputed["old_value"].startswith("2026-10-28")
    assert disputed["new_value"].startswith("2026-10-30")
    assert set(disputed["evidence_ids"]) == {"LMS-CS315-210", "NOTICE-CS315-18"}


def test_typed_record_versions_track_exam_dates_and_assignment_requirements():
    with SessionLocal() as db:
        first_exam = academic.ingest_academic_record(
            db,
            record_key="exam:CS301:midterm",
            record_kind="examination_date",
            record_value="2026-11-07",
            source_id="NOTICE-CAMPUS-78",
            source_title="Updated CS301 midterm notice",
            source_type="notice",
            content="The CS301 midterm date has changed to November 7.",
        )
        exam = academic.ingest_academic_record(
            db,
            record_key="exam:CS301:midterm",
            record_kind="examination_date",
            record_value="2026-11-07",
            source_id="EMAIL-CS301-EXAM-01",
            source_title="CS301 exam date confirmation",
            source_type="email",
            content="The CS301 midterm is scheduled for November 7.",
        )
        requirement = academic.ingest_academic_record(
            db,
            record_key="assignment:2:requirements",
            record_kind="assignment_requirement",
            record_value="Normalized schema, query report, and reflection",
            source_id="LMS-CS315-REQ-211",
            source_title="Updated DBMS lab instructions",
            source_type="lms",
            content="Add a short reflection to the submission.",
        )
        notice = academic.ingest_academic_record(
            db,
            record_key="notice:semester-calendar",
            record_kind="notice",
            record_value="Campus open on October 31",
            source_id="NOTICE-SEMESTER-02",
            source_title="Revised academic calendar notice",
            source_type="notice",
            content="The campus will remain open on October 31.",
        )
        history = academic.change_history(db)
    exam_change = next(item for item in history if item["source_id"] == "NOTICE-CAMPUS-78")
    requirement_change = next(item for item in history if item["source_id"] == "LMS-CS315-REQ-211")
    notice_change = next(item for item in history if item["source_id"] == "NOTICE-SEMESTER-02")
    assert first_exam["changed"] is True
    assert first_exam["change"]["status"] == "awaiting_confirmation"
    assert exam["changed"] is False
    assert exam_change["entity_type"] == "examination"
    assert exam_change["old_value"] == "2026-11-06"
    assert exam_change["new_value"] == "2026-11-07"
    assert exam_change["status"] == "verified"
    assert set(exam_change["evidence_ids"]) == {"NOTICE-CAMPUS-78", "EMAIL-CS301-EXAM-01"}
    assert requirement_change["assignment"] == "Normalization & SQL lab"
    assert requirement_change["field"] == "assignment_requirement"
    assert requirement_change["old_value"] == "Normalized schema and query report"
    assert requirement_change["status"] == "awaiting_confirmation"
    assert notice["changed"] is True
    assert notice_change["entity_type"] == "notice"
    assert notice_change["old_value"] == "Campus closed on October 31"
    assert notice_change["new_value"] == "Campus open on October 31"


def test_deadline_conflict_detection_includes_time_changes_on_the_same_date():
    with SessionLocal() as db:
        result = academic.ingest_academic_record(
            db,
            record_key="assignment:2:deadline",
            record_kind="deadline",
            record_value="2026-10-28T12:00:00+05:30",
            source_id="NOTICE-CS315-TIME",
            source_title="DBMS submission time update",
            source_type="notice",
            content="The submission closes at noon on October 28.",
        )
        conflicts = academic.deadline_conflicts(db)
    assert result["change"]["status"] == "disputed"
    assert conflicts[0]["assignment_id"] == 2


def test_assistant_separates_facts_conflicts_and_recommendations():
    with SessionLocal() as db:
        academic.publish_demo_notice(db)
        response = academic.ask_academic_question("What changed this week?", db)
    assert response["mode"] == "deterministic_demo"
    assert response["verified_facts"][0]["source_ids"] == ["LMS-CS301-104", "EMAIL-CS301-32"]
    assert response["conflicts"][0]["status"] == "conflicting"
    assert response["recommendations"]


def test_study_plan_is_pending_until_decision_and_audited():
    with SessionLocal() as db:
        proposal = academic.create_study_plan(db, "test-student")
        assert proposal.status == "pending"
        assert proposal.payload["sessions"]
        academic.decide_proposal(db, proposal, "test-student", True)
        assert proposal.status == "approved"


def test_digital_twin_recalculates_loss_and_keeps_dispute_uncertainty_separate():
    with SessionLocal() as db:
        academic.publish_demo_notice(db)
        baseline = academic.simulate_workload(db, {"lost_hours_tomorrow": 0})
        scenario = academic.simulate_workload(db, {"lost_hours_tomorrow": 2})
    assert scenario["scenario"]["lost_hours_tomorrow"] == 2
    assert any("removes 2 available hours" in item for item in scenario["assumptions"])
    base_risk = next(item for item in baseline["risks"] if item["assignment_id"] == 2)
    changed_risk = next(item for item in scenario["risks"] if item["assignment_id"] == 2)
    assert changed_risk["deadline_uncertainty"]["status"] == "disputed"
    assert changed_risk["deadline_uncertainty"]["window_start"] == "2026-10-28"
    assert changed_risk["deadline_uncertainty"]["window_end"] == "2026-10-30"
    assert changed_risk["uncertainty_points"] == 12
    assert base_risk["uncertainty_points"] == 12
    assert changed_risk["workload_score"] == base_risk["workload_score"]
    assert "not treated as confirmed" in changed_risk["deadline_uncertainty"]["explanation"]
    assert scenario["summary"]["available_capacity_hours"] < baseline["summary"]["available_capacity_hours"]
    assert scenario["schedule"]
    assert scenario["alternatives"]


def test_twin_scenarios_cover_new_work_estimate_and_session_move_without_persisting():
    with SessionLocal() as db:
        base_preferences = academic.twin_preferences_data(db)
        result = academic.simulate_workload(db, {
            "lost_hours_tomorrow": 2,
            "additional_assignment": {
                "title": "Scenario lab",
                "due_date": "2026-10-26",
                "estimated_hours": 2,
                "course_code": "CS999",
            },
            "increase_estimate": {"assignment_id": 1, "extra_hours": 1},
            "move_session": {"session_id": "study-cs301-2026-10-23", "to_date": "2026-10-24"},
        })
        after_preferences = academic.twin_preferences_data(db)
        assignment_count = len(academic.list_assignments(db))
    assert result["summary"]["task_count"] == 5
    assert assignment_count == 4
    assert result["planned_sessions"][0]["date"] == "2026-10-24"
    assert base_preferences == after_preferences


def test_revised_plan_proposal_requires_review_and_records_outcome():
    with SessionLocal() as db:
        proposal = academic.create_revised_plan(db, "student", {"lost_hours_tomorrow": 2})
        assert proposal.status == "pending"
        assert proposal.payload["outcome"] == "pending_student_review"
        assert proposal.payload["scenario"]["lost_hours_tomorrow"] == 2
        academic.decide_proposal(db, proposal, "student", True)
        assert proposal.payload["outcome"] == "approved_no_external_calendar_write"
