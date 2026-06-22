"""Add user_id (claimed-by) column to organization table.

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-06-23 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "h2i3j4k5l6m7"
down_revision = "g1h2i3j4k5l6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "organization",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_organization_user_id",
        "organization",
        "user",
        ["user_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_organization_user_id", "organization", type_="foreignkey")
    op.drop_column("organization", "user_id")
