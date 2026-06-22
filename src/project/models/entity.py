"""New consolidated entity model layer (Phase 1b).

Adds Person, Organization, Affiliation, InvestorProfile, Geography and the
polymorphic entity_* facet join tables (EntityIndustry, EntityStage,
EntityGeography, EntityNotable) plus EntityBookmark.

Also hosts NotableInvestment (relocated from investor.py in Phase 2d Task 1).

Discriminator pattern:
    Polymorphic references use a (entity_type: EntityType, entity_id: int)
    pair.  There is NO shared surrogate entity table and NO DB-level FK on
    entity_id (integrity is enforced at the ORM / application layer).  This
    mirrors the Typesense composite-id scheme (f'{entity_type}_{db_id}') and
    lets the discriminator drive the entity_type search facet directly.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    exists,
    func,
    text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..extensions import db
from ..utils.enums import (
    AffiliationRole,
    EntityType,
    InvestmentStage,
    InvestorType,
    LeadPreference,
    OrgType,
)

if TYPE_CHECKING:
    from .helpers import Industry
    from .user import User


# ---------------------------------------------------------------------------
# NotableInvestment — relocated from investor.py (Phase 2d Task 1)
# ---------------------------------------------------------------------------


class NotableInvestment(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "id": self.id,
            "name": self.name,
        }

    @staticmethod
    def get_all() -> Sequence[NotableInvestment]:
        return db.session.scalars(db.select(NotableInvestment)).all()

    @staticmethod
    def get_by_id(id: int) -> NotableInvestment | None:
        return db.session.scalar(db.select(NotableInvestment).where(NotableInvestment.id == id))

    @staticmethod
    def get_by_name(name: str) -> NotableInvestment | None:
        return db.session.scalar(db.select(NotableInvestment).where(NotableInvestment.name == name))

    @staticmethod
    def get_by_id_list(id_list) -> Sequence[NotableInvestment]:
        if len(id_list) == 0:
            return []
        valid_id_list = [i for i in id_list if isinstance(i, int)]
        stmt = db.select(NotableInvestment).where(NotableInvestment.id.in_(valid_id_list))
        industries = db.session.execute(stmt).scalars().all()
        return industries


class Person(MappedAsDataclass, db.Model, unsafe_hash=True):
    """A natural person in the investor directory."""

    __tablename__ = "person"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    last_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    about: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    headline: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    website: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    linkedin: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    twitter: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    email: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("user.id"), nullable=True, default=None)
    search_index: Mapped[str | None] = mapped_column(String, nullable=True, default=None, init=False)
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True, init=False
    )

    # Relationships (init=False — not set via constructor)
    user: Mapped[User | None] = relationship("User", foreign_keys=[user_id], uselist=False, init=False)

    def __repr__(self) -> str:
        return f"<Person {self.first_name} {self.last_name or ''}>"

    @staticmethod
    def get_by_slug(slug: str) -> Person | None:
        """Return the public Person with the given slug, or None."""
        return db.session.scalar(db.select(Person).where(Person.slug == slug, Person.is_public.is_(True)))

    @staticmethod
    def get_by_id(id: int) -> Person | None:
        return db.session.scalar(db.select(Person).where(Person.id == id))

    @staticmethod
    def get_all() -> Sequence[Person]:
        return db.session.scalars(db.select(Person)).all()

    @staticmethod
    def get_by_user_id(user_id: int) -> Person | None:
        return db.session.scalar(db.select(Person).where(Person.user_id == user_id))

    def set_slug(self) -> None:
        import uuid as _uuid

        from slugify import slugify

        base_slug = slugify(f"{self.first_name} {self.last_name or ''}")
        existing = db.session.scalar(db.select(Person).where(Person.slug == base_slug))
        if existing and existing.id != self.id:
            base_slug = f"{base_slug}-{_uuid.uuid4().hex[:4]}"
        self.slug = base_slug
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            self.slug = f"{base_slug}-{_uuid.uuid4().hex[:4]}"
            db.session.commit()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name or ''}".strip()


class Organization(MappedAsDataclass, db.Model, unsafe_hash=True):
    """An investment firm, accelerator, or other investing organization."""

    __tablename__ = "organization"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    org_type: Mapped[OrgType] = mapped_column(SQLEnum(OrgType, name="org_type"), nullable=False)

    about: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    website: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    linkedin: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    twitter: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    email: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    n_employees: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    search_index: Mapped[str | None] = mapped_column(String, nullable=True, default=None, init=False)
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True, init=False
    )

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"

    @staticmethod
    def get_by_slug(slug: str) -> Organization | None:
        """Return the public Organization with the given slug, or None."""
        return db.session.scalar(
            db.select(Organization).where(Organization.slug == slug, Organization.is_public.is_(True))
        )

    @staticmethod
    def get_by_id(id: int) -> Organization | None:
        return db.session.scalar(db.select(Organization).where(Organization.id == id))

    @staticmethod
    def get_all() -> Sequence[Organization]:
        return db.session.scalars(db.select(Organization)).all()

    @staticmethod
    def get_by_email(email: str) -> Organization | None:
        return db.session.scalar(db.select(Organization).where(Organization.email == email))

    def set_slug(self) -> None:
        import uuid as _uuid

        from slugify import slugify

        base_slug = slugify(self.name)
        existing = db.session.scalar(db.select(Organization).where(Organization.slug == base_slug))
        if existing and existing.id != self.id:
            base_slug = f"{base_slug}-{_uuid.uuid4().hex[:4]}"
        self.slug = base_slug
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            self.slug = f"{base_slug}-{_uuid.uuid4().hex[:4]}"
            db.session.commit()


class Affiliation(MappedAsDataclass, db.Model, unsafe_hash=True):
    """Edge between a Person and an Organization (replaces Investor.firm_name)."""

    __tablename__ = "affiliation"
    __table_args__ = (UniqueConstraint("person_id", "organization_id", "role", name="uq_affiliation_person_org_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("person.id"), nullable=False)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organization.id"), nullable=False)
    role: Mapped[AffiliationRole] = mapped_column(SQLEnum(AffiliationRole, name="affiliation_role"), nullable=False)

    title: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    # Relationships
    person: Mapped[Person] = relationship("Person", foreign_keys=[person_id], init=False)
    organization: Mapped[Organization] = relationship("Organization", foreign_keys=[organization_id], init=False)

    def __repr__(self) -> str:
        return f"<Affiliation person_id={self.person_id} org_id={self.organization_id} role={self.role}>"


class InvestorProfile(MappedAsDataclass, db.Model, unsafe_hash=True):
    """Investment-specific metadata for either a Person or an Organization.

    Uses a (entity_type, entity_id) discriminator pair — no shared surrogate
    entity table, no DB-level FK on entity_id.
    """

    __tablename__ = "investor_profile"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", name="uq_investor_profile_entity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    entity_type: Mapped[EntityType] = mapped_column(SQLEnum(EntityType, name="entity_type"), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)

    investor_type: Mapped[InvestorType | None] = mapped_column(
        SQLEnum(InvestorType, name="investor_type"), nullable=True, default=None
    )
    min_investment: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=None)
    max_investment: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=None)
    n_investments: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    n_exits: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    thesis: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    lead_pref: Mapped[LeadPreference | None] = mapped_column(
        SQLEnum(LeadPreference, name="lead_preference"), nullable=True, default=None
    )
    accepts_cold_inbound: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    def __repr__(self) -> str:
        return f"<InvestorProfile {self.entity_type}:{self.entity_id}>"


class Geography(MappedAsDataclass, db.Model, unsafe_hash=True):
    """A geographic unit (country, region, or city) used for faceted filtering."""

    __tablename__ = "geography"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # "country" | "region" | "city"

    country_code: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<Geography {self.slug} ({self.type})>"


# ---------------------------------------------------------------------------
# Polymorphic facet join tables
# Each table uses (entity_type, entity_id) discriminator + one facet column.
# ---------------------------------------------------------------------------


class EntityIndustry(MappedAsDataclass, db.Model, unsafe_hash=True):
    """Links a Person or Organization to an Industry (replaces investor_industry / investment_firm_industry M2M)."""

    __tablename__ = "entity_industry"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "industry_id", name="uq_entity_industry"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    entity_type: Mapped[EntityType] = mapped_column(SQLEnum(EntityType, name="entity_type"), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    industry_id: Mapped[int] = mapped_column(Integer, ForeignKey("industry.id"), nullable=False)

    def __repr__(self) -> str:
        return f"<EntityIndustry {self.entity_type}:{self.entity_id} industry={self.industry_id}>"


class EntityStage(MappedAsDataclass, db.Model, unsafe_hash=True):
    """Investment stage preference for a Person or Organization (replaces investor_round / investment_firm_round M2M)."""

    __tablename__ = "entity_stage"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "stage", name="uq_entity_stage"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    entity_type: Mapped[EntityType] = mapped_column(SQLEnum(EntityType, name="entity_type"), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[InvestmentStage] = mapped_column(SQLEnum(InvestmentStage, name="investment_stage"), nullable=False)

    def __repr__(self) -> str:
        return f"<EntityStage {self.entity_type}:{self.entity_id} stage={self.stage}>"


class EntityGeography(MappedAsDataclass, db.Model, unsafe_hash=True):
    """Links a Person or Organization to a Geography for faceted filtering."""

    __tablename__ = "entity_geography"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "geography_id", name="uq_entity_geography"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    entity_type: Mapped[EntityType] = mapped_column(SQLEnum(EntityType, name="entity_type"), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    geography_id: Mapped[int] = mapped_column(Integer, ForeignKey("geography.id"), nullable=False)

    # Relationship
    geography: Mapped[Geography] = relationship("Geography", foreign_keys=[geography_id], init=False)

    def __repr__(self) -> str:
        return f"<EntityGeography {self.entity_type}:{self.entity_id} geo={self.geography_id}>"


class EntityNotable(MappedAsDataclass, db.Model, unsafe_hash=True):
    """Links a Person or Organization to a NotableInvestment (replaces investor_notable_investment M2M)."""

    __tablename__ = "entity_notable"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "notable_investment_id", name="uq_entity_notable"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    entity_type: Mapped[EntityType] = mapped_column(SQLEnum(EntityType, name="entity_type"), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    notable_investment_id: Mapped[int] = mapped_column(Integer, ForeignKey("notable_investment.id"), nullable=False)

    def __repr__(self) -> str:
        return f"<EntityNotable {self.entity_type}:{self.entity_id} notable={self.notable_investment_id}>"


class EntityBookmark(MappedAsDataclass, db.Model, unsafe_hash=True):
    """A user's bookmark of a Person or Organization (replaces InvestorBookmark + InvestmentFirmBookmark)."""

    __tablename__ = "entity_bookmark"
    __table_args__ = (UniqueConstraint("user_id", "entity_type", "entity_id", name="uq_entity_bookmark_user_entity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(SQLEnum(EntityType, name="entity_type"), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True, init=False
    )

    # Relationships
    user: Mapped[User] = relationship("User", foreign_keys=[user_id], init=False)

    def __repr__(self) -> str:
        return f"<EntityBookmark user={self.user_id} {self.entity_type}:{self.entity_id}>"

    @staticmethod
    def get_by_user_id(user_id: int) -> Sequence[EntityBookmark]:
        return db.session.scalars(db.select(EntityBookmark).where(EntityBookmark.user_id == user_id)).all()

    @staticmethod
    def exists(user_id: int, entity_type: EntityType, entity_id: int) -> bool:
        return db.session.scalar(
            db.select(
                exists().where(
                    EntityBookmark.user_id == user_id,
                    EntityBookmark.entity_type == entity_type,
                    EntityBookmark.entity_id == entity_id,
                )
            )
        )


# ---------------------------------------------------------------------------
# Module-level query helpers
# ---------------------------------------------------------------------------


def load_profile_bundle(entity_type: EntityType, entity_id: int) -> dict:
    """Load all profile facets for a Person or Organization in grouped queries.

    Returns a dict with keys:
        profile     – InvestorProfile row or None
        industries  – list[Industry]
        stages      – list[InvestmentStage]  (enum values from EntityStage rows)
        geographies – list[Geography]
        notables    – list[NotableInvestment]
        affiliations – list[Affiliation]
            For PERSON: rows where person_id == entity_id
            For ORG:    rows where organization_id == entity_id

    Uses one db.select per facet kind (no per-row loops).
    """
    # Deferred imports to avoid circular imports at module load time
    from .helpers import Industry

    # --- InvestorProfile -------------------------------------------------------
    profile: InvestorProfile | None = db.session.scalar(
        db.select(InvestorProfile).where(
            InvestorProfile.entity_type == entity_type,
            InvestorProfile.entity_id == entity_id,
        )
    )

    # --- Industries ------------------------------------------------------------
    industries: list[Industry] = list(
        db.session.scalars(
            db.select(Industry)
            .join(EntityIndustry, EntityIndustry.industry_id == Industry.id)
            .where(
                EntityIndustry.entity_type == entity_type,
                EntityIndustry.entity_id == entity_id,
            )
        ).all()
    )

    # --- Stages (return the InvestmentStage enum values) ----------------------
    stages: list[InvestmentStage] = list(
        db.session.scalars(
            db.select(EntityStage.stage).where(
                EntityStage.entity_type == entity_type,
                EntityStage.entity_id == entity_id,
            )
        ).all()
    )

    # --- Geographies -----------------------------------------------------------
    geographies: list[Geography] = list(
        db.session.scalars(
            db.select(Geography)
            .join(EntityGeography, EntityGeography.geography_id == Geography.id)
            .where(
                EntityGeography.entity_type == entity_type,
                EntityGeography.entity_id == entity_id,
            )
        ).all()
    )

    # --- Notable investments ---------------------------------------------------
    notables: list[NotableInvestment] = list(
        db.session.scalars(
            db.select(NotableInvestment)
            .join(EntityNotable, EntityNotable.notable_investment_id == NotableInvestment.id)
            .where(
                EntityNotable.entity_type == entity_type,
                EntityNotable.entity_id == entity_id,
            )
        ).all()
    )

    # --- Affiliations ----------------------------------------------------------
    if entity_type == EntityType.PERSON:
        affiliations: list[Affiliation] = list(
            db.session.scalars(db.select(Affiliation).where(Affiliation.person_id == entity_id)).all()
        )
    else:
        affiliations = list(
            db.session.scalars(db.select(Affiliation).where(Affiliation.organization_id == entity_id)).all()
        )

    return {
        "profile": profile,
        "industries": industries,
        "stages": stages,
        "geographies": geographies,
        "notables": notables,
        "affiliations": affiliations,
    }
