"""add industry.slug column with backfill

Revision ID: d1e2f3a4b5c6
Revises: c3d4e5f6a7b8
Create Date: 2026-06-22 00:00:00.000000

Adds a nullable `slug` column to the `industry` table, backfills existing rows
using python-slugify, then adds a unique index.  The column stays nullable to
allow a zero-downtime deploy: after backfill it will effectively be non-null for
all existing rows, but we do NOT change nullable=False here to avoid a full-table
rewrite on large Postgres tables.
"""

import sqlalchemy as sa
from alembic import op
from slugify import slugify

revision = "d1e2f3a4b5c6"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add the nullable slug column
    with op.batch_alter_table("industry", schema=None) as batch_op:
        batch_op.add_column(sa.Column("slug", sa.String(), nullable=True))

    # 2. Backfill: set slug = slugify(name) for all existing rows
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, name FROM industry")).fetchall()
    for row in rows:
        row_id, name = row[0], row[1]
        slug_value = slugify(name)
        conn.execute(
            sa.text("UPDATE industry SET slug = :slug WHERE id = :id"),
            {"slug": slug_value, "id": row_id},
        )

    # 3. Add unique index on industry.slug
    with op.batch_alter_table("industry", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_industry_slug", ["slug"])


def downgrade():
    with op.batch_alter_table("industry", schema=None) as batch_op:
        batch_op.drop_constraint("uq_industry_slug", type_="unique")
        batch_op.drop_column("slug")
