import httpx
import pytest
from dataclasses import replace

import backend.main as web_app
from backend.main import app, login_attempts


@pytest.mark.asyncio
async def test_login_and_academic_api_permissions():
    login_attempts.clear()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        denied = await client.get("/api/dashboard")
        assert denied.status_code == 401

        bad_login = await client.post(
            "/api/login", json={"username": "wrong", "password": "not-the-password"}
        )
        assert bad_login.status_code == 401
        login = await client.post(
            "/api/login",
            json={"username": "test-user", "password": "test-password-that-is-long-enough"},
        )
        assert login.status_code == 200
        assert (await client.get("/api/session")).json()["authenticated"] is True

        response = await client.get("/api/dashboard")
        assert response.status_code == 200
        dashboard = response.json()
        assert dashboard["stats"]["courses"] == 4
        assert dashboard["stats"]["conflicts"] == 0
        assert dashboard["assignments"][1]["due_at"].startswith("2026-10-28")
        assert dashboard["changes"][0]["assignment"] == "Graph algorithms problem set"
        published = await client.post("/api/demo/publish-notice")
        assert published.status_code == 200
        assert published.json()["created"] is True
        radar = await client.get("/api/radar")
        assert radar.json()["conflicts"][0]["status"] == "conflicting"
        assert next(item for item in radar.json()["history"] if item["assignment_id"] == 2)["status"] == "disputed"
        baseline = await client.post("/api/twin/simulate", json={"lost_hours_tomorrow": 0})
        simulation = await client.post("/api/twin/simulate", json={"lost_hours_tomorrow": 2})
        assert simulation.status_code == 200
        twin = simulation.json()
        assert twin["scenario"]["lost_hours_tomorrow"] == 2
        assert twin["summary"]["available_capacity_hours"] == baseline.json()["summary"]["available_capacity_hours"] - 2
        disputed_risk = next(item for item in twin["risks"] if item["assignment_id"] == 2)
        assert disputed_risk["deadline_uncertainty"]["status"] == "disputed"
        assert disputed_risk["uncertainty_points"] == 12
        proposal_response = await client.post("/api/twin/proposals", json={"lost_hours_tomorrow": 2})
        assert proposal_response.status_code == 200
        proposal = proposal_response.json()
        assert proposal["status"] == "pending"
        assert proposal["payload"]["outcome"] == "pending_student_review"
        approved = await client.post(
            f"/api/proposals/{proposal['id']}/decision",
            json={"approved": True},
        )
        assert approved.status_code == 200
        assert approved.json()["payload"]["outcome"] == "approved_no_external_calendar_write"
        reset = await client.post("/api/demo/reset")
        assert reset.status_code == 200
        reset_dashboard = await client.get("/api/dashboard")
        assert reset_dashboard.json()["stats"]["conflicts"] == 0
        assert reset_dashboard.json()["assignments"][1]["due_at"].startswith("2026-10-28")
        exam_update = await client.post("/api/radar/records", json={
            "record_key": "exam:CS301:midterm",
            "record_kind": "examination_date",
            "record_value": "2026-11-07",
            "source_id": "NOTICE-CAMPUS-78",
            "source_title": "Updated CS301 midterm notice",
            "source_type": "notice",
            "content": "The CS301 midterm date has changed to November 7.",
        })
        requirement_update = await client.post("/api/radar/records", json={
            "record_key": "assignment:2:requirements",
            "record_kind": "assignment_requirement",
            "record_value": "Normalized schema, query report, and reflection",
            "source_id": "LMS-CS315-REQ-211",
            "source_title": "Updated DBMS lab instructions",
            "source_type": "lms",
            "content": "Add a short reflection to the submission.",
        })
        assert exam_update.status_code == 200
        assert exam_update.json()["change"]["entity_type"] == "examination"
        assert requirement_update.status_code == 200
        assert requirement_update.json()["change"]["field"] == "assignment_requirement"
        assert (await client.get("/api/radar")).json()["history"][0]["source_id"] == "LMS-CS315-REQ-211"
        answer = await client.post("/api/chat", json={"message": "Which dates are conflicting?"})
        assert answer.status_code == 200
        assert answer.json()["mode"] == "deterministic_demo"
        assert answer.json()["conflicts"] == []
        assert (await client.post("/api/logout")).status_code == 200
        assert (await client.get("/api/session")).json()["authenticated"] is False


@pytest.mark.asyncio
async def test_study_plan_requires_an_explicit_decision(monkeypatch):
    monkeypatch.setattr(
        web_app,
        "settings",
        replace(web_app.settings, allowed_origins=("http://127.0.0.1:5173",)),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        await client.post(
            "/api/login",
            json={"username": "test-user", "password": "test-password-that-is-long-enough"},
        )
        cross_origin = await client.post(
            "/api/proposals",
            headers={"origin": "https://attacker.invalid"},
        )
        assert cross_origin.status_code == 403
        wrong_scheme = await client.post(
            "/api/login",
            headers={"origin": "https://testserver"},
            json={"username": "test-user", "password": "not-the-password"},
        )
        assert wrong_scheme.status_code == 403
        dev_origin = await client.post(
            "/api/proposals",
            headers={"origin": "http://127.0.0.1:5173"},
        )
        assert dev_origin.status_code == 200
        await client.post(
            f"/api/proposals/{dev_origin.json()['id']}/decision",
            headers={"origin": "http://127.0.0.1:5173"},
            json={"approved": False},
        )
        created = await client.post("/api/proposals")
        assert created.status_code == 200
        proposal = created.json()
        assert proposal["status"] == "pending"
        assert "does not modify your calendar" in proposal["payload"]["notice"]

        decision = await client.post(
            f"/api/proposals/{proposal['id']}/decision",
            json={"approved": True},
        )
        assert decision.status_code == 200
        assert decision.json()["status"] == "approved"
        duplicate = await client.post(
            f"/api/proposals/{proposal['id']}/decision",
            json={"approved": False},
        )
        assert duplicate.status_code == 409
        audit = await client.get("/api/audit")
        assert any(item["action"] == "approved" for item in audit.json())
        await client.post("/api/logout")


@pytest.mark.asyncio
async def test_login_rate_limit_and_same_origin():
    login_attempts.clear()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        for _ in range(5):
            response = await client.post(
                "/api/login",
                json={"username": "wrong", "password": "not-the-password"},
            )
            assert response.status_code == 401
        limited = await client.post(
            "/api/login",
            json={"username": "test-user", "password": "test-password-that-is-long-enough"},
        )
        assert limited.status_code == 429

        cross_origin = await client.post(
            "/api/login",
            headers={"origin": "https://attacker.invalid"},
            json={"username": "test-user", "password": "test-password-that-is-long-enough"},
        )
        assert cross_origin.status_code == 403
