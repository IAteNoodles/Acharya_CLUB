"""remove_late_attendance

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-12 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL doesn't support DROP VALUE natively, so we recreate the type
    op.execute("ALTER TYPE attendancestatus RENAME TO attendancestatus_old")
    op.execute("CREATE TYPE attendancestatus AS ENUM('present', 'absent')")
    op.execute(
        "ALTER TABLE attendance ALTER COLUMN status TYPE attendancestatus USING "
        "status::text::attendancestatus"
    )
    op.execute("DROP TYPE attendancestatus_old")


def downgrade() -> None:
    op.execute("ALTER TYPE attendancestatus RENAME TO attendancestatus_new")
    op.execute("CREATE TYPE attendancestatus AS ENUM('present', 'absent', 'late')")
    op.execute(
        "ALTER TABLE attendance ALTER COLUMN status TYPE attendancestatus USING "
        "status::text::attendancestatus"
    )
    op.execute("DROP TYPE attendancestatus_new")
