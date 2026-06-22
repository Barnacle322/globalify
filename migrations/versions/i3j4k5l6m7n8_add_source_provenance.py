"""Add source-provenance columns to person and organization.

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-06-23 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "i3j4k5l6m7n8"
down_revision = "h2i3j4k5l6m7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("person", sa.Column("source", sa.String(), nullable=True))
    op.add_column("person", sa.Column("source_id", sa.String(), nullable=True))
    op.add_column("person", sa.Column("source_url", sa.String(), nullable=True))
    op.add_column("person", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_person_source", "person", ["source", "source_id"])

    op.add_column("organization", sa.Column("source", sa.String(), nullable=True))
    op.add_column("organization", sa.Column("source_id", sa.String(), nullable=True))
    op.add_column("organization", sa.Column("source_url", sa.String(), nullable=True))
    op.add_column("organization", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_organization_source", "organization", ["source", "source_id"])


def downgrade():
    op.drop_constraint("uq_organization_source", "organization", type_="unique")
    op.drop_column("organization", "last_synced_at")
    op.drop_column("organization", "source_url")
    op.drop_column("organization", "source_id")
    op.drop_column("organization", "source")

    op.drop_constraint("uq_person_source", "person", type_="unique")
    op.drop_column("person", "last_synced_at")
    op.drop_column("person", "source_url")
    op.drop_column("person", "source_id")
    op.drop_column("person", "source")
