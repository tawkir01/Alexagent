"""Create CampusFlow academic workspace tables."""

from alembic import op

from backend.db import Base
from backend import models  # noqa: F401

revision = "0001_academic_workspace"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
