"""lowercase_user_emails

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-16 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    duplicates = conn.exec_driver_sql(
        "SELECT lower(email) FROM users GROUP BY lower(email) HAVING count(*) > 1"
    ).fetchall()
    if duplicates:
        emails = ", ".join(row[0] for row in duplicates)
        raise RuntimeError(
            f"Cannot lowercase emails: case-insensitive duplicates exist for [{emails}]. "
            "Resolve these accounts manually, then re-run the migration."
        )
    op.execute("UPDATE users SET email = lower(email) WHERE email <> lower(email)")


def downgrade() -> None:
    pass
