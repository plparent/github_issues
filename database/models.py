"""Table definitions. Alembic compares these to the database to autogenerate migrations."""
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
)

metadata = MetaData()

issues = Table(
    "issues",
    metadata,
    Column("owner", Text, nullable=False),
    Column("repo", Text, nullable=False),
    Column("issue_number", Integer, nullable=False),
    Column("status", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("closed_at", DateTime(timezone=True)),
    PrimaryKeyConstraint("owner", "repo", "issue_number"),
)

# event_id is Text because commit events use a sha rather than a numeric id.
# It's still not the primary key: GitHub's ids aren't guaranteed unique across
# event types, so a surrogate key is used instead.
issue_timeline_events = Table(
    "issue_timeline_events",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("owner", Text, nullable=False),
    Column("repo", Text, nullable=False),
    Column("issue_number", Integer, nullable=False),
    Column("event_id", Text, nullable=False),
    Column("created_at", DateTime(timezone=True)),
    Column("event_type", Text, nullable=False),
    Column("actor", Text),
    ForeignKeyConstraint(
        ["owner", "repo", "issue_number"],
        ["issues.owner", "issues.repo", "issues.issue_number"],
        ondelete="CASCADE",
    ),
    UniqueConstraint("owner", "repo", "issue_number", "event_id", name="uq_timeline_event"),
    Index("idx_timeline_issue", "owner", "repo", "issue_number"),
)

sync_state = Table(
    "sync_state",
    metadata,
    Column("owner", Text, nullable=False),
    Column("repo", Text, nullable=False),
    Column("last_updated", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("owner", "repo"),
)
