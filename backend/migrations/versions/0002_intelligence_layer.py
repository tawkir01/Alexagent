"""Add CampusFlow change radar and digital twin state."""

from alembic import op
from sqlalchemy import inspect
from sqlalchemy import Integer, Column

from backend.db import Base
from backend import models  # noqa: F401

revision = "0002_intelligence_layer"
down_revision = "0001_academic_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "importance" not in {column["name"] for column in inspector.get_columns("assignments")}:
        op.add_column("assignments", Column("importance", Integer, nullable=True))
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("twin_preferences", "academic_changes"):
        if inspect(bind).has_table(table):
            op.drop_table(table)
    if "importance" in {column["name"] for column in inspect(bind).get_columns("assignments")}:
        with op.batch_alter_table("assignments") as batch:
            batch.drop_column("importance")
