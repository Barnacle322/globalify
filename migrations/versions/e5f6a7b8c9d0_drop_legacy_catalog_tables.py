"""drop legacy catalog tables (investor/investment_firm/country/M2M/backups)

Revision ID: e5f6a7b8c9d0
Revises: d1e2f3a4b5c6
Create Date: 2026-06-22 00:00:00.000000

Phase 2d Task 5 — destructive retirement of the old catalog model.

Drop order (FK-safe, children before parents):
  1. claim_request.investor_id column  (if column still exists — was not
     dropped in earlier migrations; only entity_type/entity_id were added)
  2. investor_bookmark, investment_firm_bookmark  (child rows / bookmarks)
  3. investor_backup_industry, investor_backup_notable_investment,
     investor_backup_round  (M2M children of investor_backup)
  4. investor_origin_point_industry, investor_origin_point_notable_investment,
     investor_origin_point_round  (M2M children of investor_origin_point)
  5. investor_backup, investor_origin_point  (snapshot / audit tables)
  6. investor_round, investor_industry, investor_notable_investment  (Investor M2M)
  7. investment_firm_round, investment_firm_industry,
     investment_firm_notable_investment  (InvestmentFirm M2M)
  8. investor, investment_firm  (core catalog tables)
  9. country  (lookup table; search now uses Geography.country_code)

This migration is one-way (downgrade is a best-effort stub — data is gone).
PROD migration must be gated on a DB backup before applying.
"""

import sqlalchemy as sa
from alembic import op


revision = "e5f6a7b8c9d0"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def _table_exists(conn, table_name: str) -> bool:
    """Return True if *table_name* exists in the current schema."""
    return sa.inspect(conn).has_table(table_name)


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    """Return True if *column_name* exists on *table_name*."""
    if not _table_exists(conn, table_name):
        return False
    cols = {c["name"] for c in sa.inspect(conn).get_columns(table_name)}
    return column_name in cols


def upgrade():
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # Step 1: Drop claim_request.investor_id (FK to investor.id)
    #         The column was added in 5c32ad357046 but never explicitly
    #         dropped — it was superseded by entity_type/entity_id in
    #         a1b2c3d4e5f6.  Drop it now so we can safely delete investor.
    # ------------------------------------------------------------------
    if _column_exists(conn, "claim_request", "investor_id"):
        with op.batch_alter_table("claim_request", schema=None) as batch_op:
            # Drop the FK constraint first (Postgres names it automatically)
            try:
                batch_op.drop_constraint("claim_request_investor_id_fkey", type_="foreignkey")
            except Exception:
                pass  # constraint name may vary; batch_alter handles SQLite
            batch_op.drop_column("investor_id")

    # ------------------------------------------------------------------
    # Step 2: Bookmark tables (FK to investor / investment_firm)
    # ------------------------------------------------------------------
    if _table_exists(conn, "investor_bookmark"):
        op.drop_table("investor_bookmark")

    if _table_exists(conn, "investment_firm_bookmark"):
        op.drop_table("investment_firm_bookmark")

    # ------------------------------------------------------------------
    # Step 3 & 4: investor_backup / investor_origin_point M2M children
    # ------------------------------------------------------------------
    for tbl in (
        "investor_backup_industry",
        "investor_backup_notable_investment",
        "investor_backup_round",
        "investor_origin_point_industry",
        "investor_origin_point_notable_investment",
        "investor_origin_point_round",
    ):
        if _table_exists(conn, tbl):
            op.drop_table(tbl)

    # ------------------------------------------------------------------
    # Step 5: investor_backup, investor_origin_point
    # ------------------------------------------------------------------
    if _table_exists(conn, "investor_backup"):
        op.drop_table("investor_backup")

    if _table_exists(conn, "investor_origin_point"):
        op.drop_table("investor_origin_point")

    # ------------------------------------------------------------------
    # Step 6: Investor M2M tables
    # ------------------------------------------------------------------
    for tbl in (
        "investor_round",
        "investor_industry",
        "investor_notable_investment",
    ):
        if _table_exists(conn, tbl):
            op.drop_table(tbl)

    # ------------------------------------------------------------------
    # Step 7: InvestmentFirm M2M tables
    # ------------------------------------------------------------------
    for tbl in (
        "investment_firm_round",
        "investment_firm_industry",
        "investment_firm_notable_investment",
    ):
        if _table_exists(conn, tbl):
            op.drop_table(tbl)

    # ------------------------------------------------------------------
    # Step 8: Core catalog tables
    # ------------------------------------------------------------------
    if _table_exists(conn, "investor"):
        op.drop_table("investor")

    if _table_exists(conn, "investment_firm"):
        op.drop_table("investment_firm")

    # ------------------------------------------------------------------
    # Step 9: Country lookup table (replaced by Geography.country_code)
    # ------------------------------------------------------------------
    if _table_exists(conn, "country"):
        op.drop_table("country")


def downgrade():
    """Best-effort structural recreate — data is permanently gone.

    This migration is intentionally one-way.  To restore:
      1. Restore from the pre-migration DB backup.
      OR
      2. Re-run the Phase 1a/1b chain on a fresh DB (creates + backfills).
    """
    # Recreate country (no FK deps)
    op.create_table(
        "country",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("code"),
    )

    # Recreate investor
    op.create_table(
        "investor",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("slug", sa.String(), nullable=True),
        sa.Column("firm_name", sa.String(), nullable=True),
        sa.Column("about", sa.String(), nullable=True),
        sa.Column("position", sa.String(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("linkedin", sa.String(), nullable=True),
        sa.Column("twitter", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("n_investments", sa.Integer(), nullable=True),
        sa.Column("n_exits", sa.Integer(), nullable=True),
        sa.Column("min_investment", sa.BigInteger(), nullable=True),
        sa.Column("max_investment", sa.BigInteger(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("_coordinates", sa.String(), nullable=True),
        sa.Column("_country", sa.String(), nullable=True),
        sa.Column("bias", sa.Integer(), nullable=True),
        sa.Column("search_index", sa.String(), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_approved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # Recreate investment_firm
    op.create_table(
        "investment_firm",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("slug", sa.String(), nullable=True),
        sa.Column("about", sa.String(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("linkedin", sa.String(), nullable=True),
        sa.Column("twitter", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("n_investments", sa.Integer(), nullable=True),
        sa.Column("n_exits", sa.Integer(), nullable=True),
        sa.Column("n_employees", sa.Integer(), nullable=True),
        sa.Column("min_investment", sa.Integer(), nullable=True),
        sa.Column("max_investment", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("_coordinates", sa.String(), nullable=True),
        sa.Column("_country", sa.String(), nullable=True),
        sa.Column("bias", sa.Integer(), nullable=True),
        sa.Column("search_index", sa.String(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("email"),
    )

    # Recreate M2M + bookmark tables (structural only — no data)
    op.create_table(
        "investor_round",
        sa.Column("investor_id", sa.Integer(), sa.ForeignKey("investor.id"), nullable=False),
        sa.Column("round_id", sa.Integer(), sa.ForeignKey("round.id"), nullable=False),
        sa.PrimaryKeyConstraint("investor_id", "round_id"),
    )
    op.create_table(
        "investor_industry",
        sa.Column("investor_id", sa.Integer(), sa.ForeignKey("investor.id"), nullable=False),
        sa.Column("industry_id", sa.Integer(), sa.ForeignKey("industry.id"), nullable=False),
        sa.PrimaryKeyConstraint("investor_id", "industry_id"),
    )
    op.create_table(
        "investor_notable_investment",
        sa.Column("investor_id", sa.Integer(), sa.ForeignKey("investor.id"), nullable=False),
        sa.Column("notable_investment_id", sa.Integer(), sa.ForeignKey("notable_investment.id"), nullable=False),
        sa.PrimaryKeyConstraint("investor_id", "notable_investment_id"),
    )
    op.create_table(
        "investment_firm_round",
        sa.Column("investment_firm_id", sa.Integer(), sa.ForeignKey("investment_firm.id"), nullable=False),
        sa.Column("round_id", sa.Integer(), sa.ForeignKey("round.id"), nullable=False),
        sa.PrimaryKeyConstraint("investment_firm_id", "round_id"),
    )
    op.create_table(
        "investment_firm_industry",
        sa.Column("investment_firm_id", sa.Integer(), sa.ForeignKey("investment_firm.id"), nullable=False),
        sa.Column("industry_id", sa.Integer(), sa.ForeignKey("industry.id"), nullable=False),
        sa.PrimaryKeyConstraint("investment_firm_id", "industry_id"),
    )
    op.create_table(
        "investment_firm_notable_investment",
        sa.Column("investment_firm_id", sa.Integer(), sa.ForeignKey("investment_firm.id"), nullable=False),
        sa.Column("notable_investment_id", sa.Integer(), sa.ForeignKey("notable_investment.id"), nullable=False),
        sa.PrimaryKeyConstraint("investment_firm_id", "notable_investment_id"),
    )
    op.create_table(
        "investor_bookmark",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("investor_id", sa.Integer(), sa.ForeignKey("investor.id"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "investment_firm_bookmark",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("investment_firm_id", sa.Integer(), sa.ForeignKey("investment_firm.id"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "investor_backup",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("investor_id", sa.Integer(), sa.ForeignKey("investor.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("slug", sa.String(), nullable=True),
        sa.Column("firm_name", sa.String(), nullable=True),
        sa.Column("about", sa.String(), nullable=True),
        sa.Column("position", sa.String(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("linkedin", sa.String(), nullable=True),
        sa.Column("twitter", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("n_investments", sa.Integer(), nullable=True),
        sa.Column("n_exits", sa.Integer(), nullable=True),
        sa.Column("min_investment", sa.BigInteger(), nullable=True),
        sa.Column("max_investment", sa.BigInteger(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("_coordinates", sa.String(), nullable=True),
        sa.Column("_country", sa.String(), nullable=True),
        sa.Column("bias", sa.Integer(), nullable=True),
        sa.Column("search_index", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "investor_origin_point",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("investor_id", sa.Integer(), sa.ForeignKey("investor.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("slug", sa.String(), nullable=True),
        sa.Column("firm_name", sa.String(), nullable=True),
        sa.Column("about", sa.String(), nullable=True),
        sa.Column("position", sa.String(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("linkedin", sa.String(), nullable=True),
        sa.Column("twitter", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("n_investments", sa.Integer(), nullable=True),
        sa.Column("n_exits", sa.Integer(), nullable=True),
        sa.Column("min_investment", sa.BigInteger(), nullable=True),
        sa.Column("max_investment", sa.BigInteger(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("_coordinates", sa.String(), nullable=True),
        sa.Column("_country", sa.String(), nullable=True),
        sa.Column("bias", sa.Integer(), nullable=True),
        sa.Column("search_index", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Re-add investor_id to claim_request (structural only)
    with op.batch_alter_table("claim_request", schema=None) as batch_op:
        batch_op.add_column(sa.Column("investor_id", sa.Integer(), nullable=True))
