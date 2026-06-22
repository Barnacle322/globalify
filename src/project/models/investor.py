"""Legacy investor module — Phase 2d Task 4.

All legacy ORM model classes and their M2M association tables have been
removed from this module.  The read-only legacy classes now live in
models/backfill.py, which is invoked solely by the Phase 1b Alembic data
revision.

NotableInvestment was relocated to entity.py in Task 1 and is re-exported
here for backward compatibility.
"""

from .entity import NotableInvestment

__all__ = ["NotableInvestment"]
