"""add entity model

Revision ID: a1b2c3d4e5f6
Revises: a687120402a9
Create Date: 2026-06-22 00:00:00.000000

SQLAlchemy 2 uses the enum member's .name (not .value) for PG enum values when
the column is declared with SQLEnum(SomeEnum, ...).  Since all our enums are
StrEnum with UPPER_NAME = "lower_value", the PG type values must be uppercase.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'a687120402a9'
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------
    # 1. Create all PG enum types first (checkfirst=True → idempotent).
    #
    # IMPORTANT: SQLAlchemy 2.x uses the enum .name (uppercase) not .value
    # when binding values from Python StrEnum members.  All enum values
    # here therefore use UPPERCASE to match what SQLAlchemy sends.
    # ------------------------------------------------------------------
    entity_type_enum = PgEnum('PERSON', 'ORG', name='entity_type', create_type=False)
    entity_type_enum.create(op.get_bind(), checkfirst=True)

    org_type_enum = PgEnum(
        'VC_FIRM', 'MICRO_VC', 'ANGEL_GROUP', 'CORPORATE_VC', 'FAMILY_OFFICE',
        'ACCELERATOR', 'INCUBATOR', 'VENTURE_STUDIO', 'PE_FIRM', 'GROWTH_EQUITY',
        'SYNDICATE', 'LP_FUND_OF_FUNDS', 'GRANT_PROGRAM', 'GOVERNMENT_PROGRAM',
        'VENTURE_DEBT', 'CROWDFUNDING_PLATFORM', 'SEARCH_FUND', 'HEDGE_FUND', 'OTHER',
        name='org_type', create_type=False,
    )
    org_type_enum.create(op.get_bind(), checkfirst=True)

    affiliation_role_enum = PgEnum(
        'FOUNDER', 'GP', 'PARTNER', 'PRINCIPAL', 'ASSOCIATE', 'SCOUT', 'ADVISOR', 'LP', 'OPERATOR',
        name='affiliation_role', create_type=False,
    )
    affiliation_role_enum.create(op.get_bind(), checkfirst=True)

    investor_type_enum = PgEnum(
        'ANGEL', 'ANGEL_SYNDICATE', 'ANGEL_GROUP', 'SCOUT', 'MICRO_VC', 'VC_FIRM',
        'GROWTH_EQUITY', 'CORPORATE_VC', 'ACCELERATOR', 'INCUBATOR', 'VENTURE_STUDIO',
        'FAMILY_OFFICE', 'PRIVATE_EQUITY', 'VENTURE_DEBT', 'CROWDFUNDING_PLATFORM',
        'GRANT_PROGRAM', 'GOVERNMENT_PROGRAM', 'SEARCH_FUND', 'FUND_OF_FUNDS',
        'LIMITED_PARTNER', 'HEDGE_FUND', 'OTHER',
        name='investor_type', create_type=False,
    )
    investor_type_enum.create(op.get_bind(), checkfirst=True)

    investment_stage_enum = PgEnum(
        'IDEA', 'PRE_SEED', 'SEED', 'SERIES_A', 'SERIES_B', 'SERIES_C',
        'SERIES_D_PLUS', 'GROWTH', 'LATE_STAGE', 'DEBT', 'SECONDARY',
        name='investment_stage', create_type=False,
    )
    investment_stage_enum.create(op.get_bind(), checkfirst=True)

    lead_preference_enum = PgEnum(
        'LEAD', 'FOLLOW', 'BOTH', 'UNKNOWN',
        name='lead_preference', create_type=False,
    )
    lead_preference_enum.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # 2. Create new tables (use create_type=False everywhere enums appear)
    # ------------------------------------------------------------------
    op.create_table(
        'person',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('about', sa.String(), nullable=True),
        sa.Column('headline', sa.String(), nullable=True),
        sa.Column('website', sa.String(), nullable=True),
        sa.Column('linkedin', sa.String(), nullable=True),
        sa.Column('twitter', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone_number', sa.String(), nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_approved', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('search_index', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    op.create_table(
        'organization',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('org_type', PgEnum(
            'VC_FIRM', 'MICRO_VC', 'ANGEL_GROUP', 'CORPORATE_VC', 'FAMILY_OFFICE',
            'ACCELERATOR', 'INCUBATOR', 'VENTURE_STUDIO', 'PE_FIRM', 'GROWTH_EQUITY',
            'SYNDICATE', 'LP_FUND_OF_FUNDS', 'GRANT_PROGRAM', 'GOVERNMENT_PROGRAM',
            'VENTURE_DEBT', 'CROWDFUNDING_PLATFORM', 'SEARCH_FUND', 'HEDGE_FUND', 'OTHER',
            name='org_type', create_type=False,
        ), nullable=False),
        sa.Column('about', sa.String(), nullable=True),
        sa.Column('website', sa.String(), nullable=True),
        sa.Column('linkedin', sa.String(), nullable=True),
        sa.Column('twitter', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone_number', sa.String(), nullable=True),
        sa.Column('n_employees', sa.Integer(), nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('is_approved', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('search_index', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    op.create_table(
        'geography',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('country_code', sa.String(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    op.create_table(
        'affiliation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), sa.ForeignKey('person.id'), nullable=False),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organization.id'), nullable=False),
        sa.Column('role', PgEnum(
            'FOUNDER', 'GP', 'PARTNER', 'PRINCIPAL', 'ASSOCIATE', 'SCOUT', 'ADVISOR', 'LP', 'OPERATOR',
            name='affiliation_role', create_type=False,
        ), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('person_id', 'organization_id', 'role', name='uq_affiliation_person_org_role'),
    )

    op.create_table(
        'investor_profile',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', PgEnum(
            'PERSON', 'ORG', name='entity_type', create_type=False,
        ), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('investor_type', PgEnum(
            'ANGEL', 'ANGEL_SYNDICATE', 'ANGEL_GROUP', 'SCOUT', 'MICRO_VC', 'VC_FIRM',
            'GROWTH_EQUITY', 'CORPORATE_VC', 'ACCELERATOR', 'INCUBATOR', 'VENTURE_STUDIO',
            'FAMILY_OFFICE', 'PRIVATE_EQUITY', 'VENTURE_DEBT', 'CROWDFUNDING_PLATFORM',
            'GRANT_PROGRAM', 'GOVERNMENT_PROGRAM', 'SEARCH_FUND', 'FUND_OF_FUNDS',
            'LIMITED_PARTNER', 'HEDGE_FUND', 'OTHER',
            name='investor_type', create_type=False,
        ), nullable=True),
        sa.Column('min_investment', sa.BigInteger(), nullable=True),
        sa.Column('max_investment', sa.BigInteger(), nullable=True),
        sa.Column('n_investments', sa.Integer(), nullable=True),
        sa.Column('n_exits', sa.Integer(), nullable=True),
        sa.Column('thesis', sa.Text(), nullable=True),
        sa.Column('lead_pref', PgEnum(
            'LEAD', 'FOLLOW', 'BOTH', 'UNKNOWN',
            name='lead_preference', create_type=False,
        ), nullable=True),
        sa.Column('accepts_cold_inbound', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type', 'entity_id', name='uq_investor_profile_entity'),
    )

    op.create_table(
        'entity_industry',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', PgEnum(
            'PERSON', 'ORG', name='entity_type', create_type=False,
        ), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('industry_id', sa.Integer(), sa.ForeignKey('industry.id'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type', 'entity_id', 'industry_id', name='uq_entity_industry'),
    )

    op.create_table(
        'entity_stage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', PgEnum(
            'PERSON', 'ORG', name='entity_type', create_type=False,
        ), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('stage', PgEnum(
            'IDEA', 'PRE_SEED', 'SEED', 'SERIES_A', 'SERIES_B', 'SERIES_C',
            'SERIES_D_PLUS', 'GROWTH', 'LATE_STAGE', 'DEBT', 'SECONDARY',
            name='investment_stage', create_type=False,
        ), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type', 'entity_id', 'stage', name='uq_entity_stage'),
    )

    op.create_table(
        'entity_geography',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', PgEnum(
            'PERSON', 'ORG', name='entity_type', create_type=False,
        ), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('geography_id', sa.Integer(), sa.ForeignKey('geography.id'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type', 'entity_id', 'geography_id', name='uq_entity_geography'),
    )

    op.create_table(
        'entity_notable',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', PgEnum(
            'PERSON', 'ORG', name='entity_type', create_type=False,
        ), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('notable_investment_id', sa.Integer(), sa.ForeignKey('notable_investment.id'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type', 'entity_id', 'notable_investment_id', name='uq_entity_notable'),
    )

    op.create_table(
        'entity_bookmark',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('entity_type', PgEnum(
            'PERSON', 'ORG', name='entity_type', create_type=False,
        ), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'entity_type', 'entity_id', name='uq_entity_bookmark_user_entity'),
    )

    # ------------------------------------------------------------------
    # 3. Add entity columns to existing claim tables
    # ------------------------------------------------------------------
    with op.batch_alter_table('claim_verification', schema=None) as batch_op:
        batch_op.add_column(sa.Column('entity_type', PgEnum(
            'PERSON', 'ORG', name='entity_type', create_type=False,
        ), nullable=True))
        batch_op.add_column(sa.Column('entity_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('claim_request', schema=None) as batch_op:
        batch_op.add_column(sa.Column('entity_type', PgEnum(
            'PERSON', 'ORG', name='entity_type', create_type=False,
        ), nullable=True))
        batch_op.add_column(sa.Column('entity_id', sa.Integer(), nullable=True))


def downgrade():
    # ------------------------------------------------------------------
    # 1. Remove columns added to claim tables
    # ------------------------------------------------------------------
    with op.batch_alter_table('claim_request', schema=None) as batch_op:
        batch_op.drop_column('entity_id')
        batch_op.drop_column('entity_type')

    with op.batch_alter_table('claim_verification', schema=None) as batch_op:
        batch_op.drop_column('entity_id')
        batch_op.drop_column('entity_type')

    # ------------------------------------------------------------------
    # 2. Drop all created tables in FK-respecting order (children first)
    # ------------------------------------------------------------------
    op.drop_table('entity_bookmark')
    op.drop_table('entity_notable')
    op.drop_table('entity_geography')
    op.drop_table('entity_stage')
    op.drop_table('entity_industry')
    op.drop_table('investor_profile')
    op.drop_table('affiliation')
    op.drop_table('geography')
    op.drop_table('organization')
    op.drop_table('person')

    # ------------------------------------------------------------------
    # 3. Drop enum types (checkfirst=True → idempotent)
    # ------------------------------------------------------------------
    PgEnum(name='lead_preference', create_type=False).drop(op.get_bind(), checkfirst=True)
    PgEnum(name='investment_stage', create_type=False).drop(op.get_bind(), checkfirst=True)
    PgEnum(name='investor_type', create_type=False).drop(op.get_bind(), checkfirst=True)
    PgEnum(name='affiliation_role', create_type=False).drop(op.get_bind(), checkfirst=True)
    PgEnum(name='org_type', create_type=False).drop(op.get_bind(), checkfirst=True)
    PgEnum(name='entity_type', create_type=False).drop(op.get_bind(), checkfirst=True)
