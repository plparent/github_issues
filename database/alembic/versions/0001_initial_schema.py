"""initial schema: issues, issue_timeline_events, sync_state

Revision ID: 0001
Revises:
Create Date: 2026-09-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "issues",
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("repo", sa.Text(), nullable=False),
        sa.Column("issue_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("owner", "repo", "issue_number"),
    )

    op.create_table(
        "issue_timeline_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("repo", sa.Text(), nullable=False),
        sa.Column("issue_number", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner", "repo", "issue_number"],
            ["issues.owner", "issues.repo", "issues.issue_number"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner", "repo", "issue_number", "event_id")
    )
    op.create_index(
        "idx_timeline_issue",
        "issue_timeline_events",
        ["owner", "repo", "issue_number"],
    )

    op.create_table(
        "sync_state",
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("repo", sa.Text(), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("owner", "repo"),
    )


def downgrade():
    op.drop_table("sync_state")
    op.drop_index("idx_timeline_issue", table_name="issue_timeline_events")
    op.drop_table("issue_timeline_events")
    op.drop_table("issues")
