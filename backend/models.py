from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    instructor: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(20))
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="course")


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="upcoming")
    estimated_hours: Mapped[int] = mapped_column(Integer, default=2)
    importance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    course: Mapped[Course] = relationship(back_populates="assignments")
    deadline_evidence: Mapped[list["DeadlineEvidence"]] = relationship(back_populates="assignment")


class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(180))
    source_type: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verified: Mapped[bool] = mapped_column(Boolean, default=True)
    record_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    record_kind: Mapped[str | None] = mapped_column(String(40), nullable=True)
    record_value: Mapped[str | None] = mapped_column(Text, nullable=True)


class DeadlineEvidence(Base):
    __tablename__ = "deadline_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"))
    source_id: Mapped[int] = mapped_column(ForeignKey("source_records.id"))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current: Mapped[bool] = mapped_column(Boolean, default=True)
    assignment: Mapped[Assignment] = relationship(back_populates="deadline_evidence")
    source: Mapped[SourceRecord] = relationship()


class AcademicChange(Base):
    __tablename__ = "academic_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(80))
    entity_title: Mapped[str] = mapped_column(String(180))
    field_name: Mapped[str] = mapped_column(String(60))
    old_value: Mapped[str] = mapped_column(Text)
    new_value: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(String(40))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30))
    evidence_ids: Mapped[list[str]] = mapped_column(JSON)


class TwinPreferences(Base):
    __tablename__ = "twin_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    availability: Mapped[dict[str, float]] = mapped_column(JSON)
    session_minutes: Mapped[int] = mapped_column(Integer, default=60)
    planned_sessions: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    importance: Mapped[dict[str, int]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ActionProposal(Base):
    __tablename__ = "action_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(180))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor: Mapped[str] = mapped_column(String(80))


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(50))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
