"""Store typed source record versions for academic change comparisons."""

from alembic import op
from sqlalchemy import Column, String, Text, inspect

revision = "0003_source_record_versions"
down_revision = "0002_intelligence_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("source_records")}
    if "record_key" not in columns:
        op.add_column("source_records", Column("record_key", String(100), nullable=True))
    if "record_kind" not in columns:
        op.add_column("source_records", Column("record_kind", String(40), nullable=True))
    if "record_value" not in columns:
        op.add_column("source_records", Column("record_value", Text(), nullable=True))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("source_records")}
    with op.batch_alter_table("source_records") as batch:
        for name in ("record_value", "record_kind", "record_key"):
            if name in columns:
                batch.drop_column(name)
