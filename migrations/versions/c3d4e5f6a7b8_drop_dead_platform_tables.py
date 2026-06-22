"""drop dead platform tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-22 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # Drop child tables first (FK order)
    op.drop_table('investment')
    op.drop_table('funding_round')
    op.drop_table('company_bookmark')
    op.drop_table('user_company')
    op.drop_table('company_invitation')
    op.drop_table('company')
    op.drop_table('country')

    # Drop dead columns
    # user.is_investor_mode_active was added in migration a687120402a9
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('is_investor_mode_active')

    # user_info.refuse_all_invitations was added in migration f9da0a2faf7b
    with op.batch_alter_table('user_info', schema=None) as batch_op:
        batch_op.drop_column('refuse_all_invitations')


def downgrade():
    # Best-effort structural recreate (no data)
    # NOTE: This downgrade is provided structurally but the data is gone.
    with op.batch_alter_table('user_info', schema=None) as batch_op:
        batch_op.add_column(sa.Column('refuse_all_invitations', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_investor_mode_active', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    op.create_table(
        'country',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code'),
    )

    op.create_table(
        'company',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('website', sa.String(), nullable=True),
        sa.Column('slug', sa.String(), nullable=True),
        sa.Column('search_index', sa.String(), nullable=True),
        sa.Column('linkedin_url', sa.String(), nullable=True),
        sa.Column('instagram_url', sa.String(), nullable=True),
        sa.Column('twitter_url', sa.String(), nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    op.create_table(
        'company_invitation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', postgresql.ENUM('TEAM', name='companyrole', create_type=False), nullable=False),
        sa.Column('invited_by', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'user_company',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'company_bookmark',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'funding_round',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('round_type', sa.String(), nullable=True),
        sa.Column('amount', sa.BigInteger(), nullable=True),
        sa.Column('announced_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'investment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('funding_round_id', sa.Integer(), sa.ForeignKey('funding_round.id'), nullable=True),
        sa.Column('investor_id', sa.Integer(), sa.ForeignKey('investor.id'), nullable=True),
        sa.Column('investment_firm_id', sa.Integer(), sa.ForeignKey('investment_firm.id'), nullable=True),
        sa.Column('amount', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
