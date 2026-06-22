"""Pydantic response schemas for investor-related API endpoints.

Legacy schemas for Investor/InvestmentFirm ORM models have been removed
(Phase 2d Task 4).  Only the schemas still consumed by live routes are kept.
"""

from pydantic import BaseModel


class RoundSchema(BaseModel):
    id: int
    name: str


class IndustrySchema(BaseModel):
    id: int
    name: str


class MiniInvestorSchema(BaseModel):
    id: int
    name: str | None


class InvestorSchema(BaseModel):
    id: int
    name: str | None
    slug: str | None
    firm_name: str | None
    about: str | None
    position: str | None
    website: str | None = None
    linkedin: str | None = None
    twitter: str | None = None
    email: str | None = None
    phone_number: str | None = None
    n_investments: int | None
    n_exits: int | None
    min_max_investment: str | None
    location: str | None
    notable_investments: list[object] | None
    rounds: list[object] | None
    industries: list[object] | None
    user_id: int | None


class OrganizationSchema(BaseModel):
    """Response schema for Organization (firm) API endpoints (formerly InvestmentFirmSchema)."""

    id: int
    name: str | None
    slug: str | None
    about: str | None
    website: str | None
    linkedin: str | None
    twitter: str | None
    email: str | None
    phone_number: str | None
    n_investments: int | None
    n_exits: int | None
    n_employees: int | None
    min_max_investment: str | None
    location: str | None
    notable_investments: list[object] | None
    rounds: list[object] | None
    industries: list[object] | None
