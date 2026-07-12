"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-06-20 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(180), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column(
            "role",
            sa.Enum("student", "teacher", "admin", name="role"),
            nullable=False,
            server_default="student",
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "active", "rejected", name="userstatus"),
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_index("users_role_status_idx", "users", ["role", "status"])

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "event_type",
            sa.Enum("in_college", "out_college", name="eventtype"),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.Enum("volunteer", "participant", "both", name="eventcategory"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("draft", "pending", "approved", "rejected", name="eventstatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("venue", sa.String(300), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_registrations", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("coordinator_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("events_status_type_idx", "events", ["status", "event_type"])
    op.create_index("events_coordinator_id_idx", "events", ["coordinator_id"])
    op.create_index("events_created_by_idx", "events", ["created_by"])
    op.create_index("events_start_date_idx", "events", ["start_date"])

    op.create_table(
        "registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "role_type",
            sa.Enum("volunteer", "participant", name="registrationrole"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "accepted", "rejected", name="registrationstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("event_id", "student_id", "role_type", name="uq_reg_event_student_role"),
    )
    op.create_index("reg_student_id_idx", "registrations", ["student_id"])
    op.create_index("reg_event_status_idx", "registrations", ["event_id", "status"])

    op.create_table(
        "attendance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("marked_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("attendance_date", sa.Date, nullable=False),
        sa.Column(
            "status",
            sa.Enum("present", "absent", "late", name="attendancestatus"),
            nullable=False,
            server_default="present",
        ),
        sa.Column("marked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("event_id", "student_id", "attendance_date", name="uq_att_event_student_date"),
    )
    op.create_index("att_event_date_idx", "attendance", ["event_id", "attendance_date"])
    op.create_index("att_student_id_idx", "attendance", ["student_id"])


def downgrade() -> None:
    op.drop_table("attendance")
    op.drop_table("registrations")
    op.drop_table("events")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS attendancestatus")
    op.execute("DROP TYPE IF EXISTS registrationstatus")
    op.execute("DROP TYPE IF EXISTS registrationrole")
    op.execute("DROP TYPE IF EXISTS eventstatus")
    op.execute("DROP TYPE IF EXISTS eventcategory")
    op.execute("DROP TYPE IF EXISTS eventtype")
    op.execute("DROP TYPE IF EXISTS userstatus")
    op.execute("DROP TYPE IF EXISTS role")
