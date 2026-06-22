"""backfill entity model

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-22 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # Guard: no-op if person table already has rows
    count = bind.execute(sa.text("SELECT COUNT(*) FROM person")).scalar()
    if count > 0:
        return

    # Guard: no-op if there's nothing to backfill (empty old catalog)
    inv_count = bind.execute(sa.text("SELECT COUNT(*) FROM investor")).scalar()
    if inv_count == 0:
        return

    session = Session(bind=bind)
    from src.project.models.backfill import backfill_entities
    counts = backfill_entities(session)
    print(f"Backfill counts: {counts}")


def downgrade():
    # This data migration is intentionally one-way (irreversible).
    # To reverse: manually delete rows from person, organization, affiliation,
    # investor_profile, geography, entity_* tables, and entity_bookmark.
    pass
