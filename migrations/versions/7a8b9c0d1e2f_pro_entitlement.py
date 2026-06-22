"""add Pro entitlement columns to user_payment

Revision ID: 7a8b9c0d1e2f
Revises: 2860207818f1
Create Date: 2026-06-22 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "7a8b9c0d1e2f"
down_revision = "2860207818f1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user_payment", sa.Column("is_pro", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("user_payment", sa.Column("pro_source", sa.String(), nullable=True))
    op.add_column("user_payment", sa.Column("pro_expires_at", sa.DateTime(), nullable=True))
    op.add_column("user_payment", sa.Column("paddle_customer_id", sa.String(), nullable=True))
    op.add_column("user_payment", sa.Column("paddle_subscription_id", sa.String(), nullable=True))


def downgrade():
    op.drop_column("user_payment", "paddle_subscription_id")
    op.drop_column("user_payment", "paddle_customer_id")
    op.drop_column("user_payment", "pro_expires_at")
    op.drop_column("user_payment", "pro_source")
    op.drop_column("user_payment", "is_pro")
