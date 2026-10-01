"""DSVA v0.9 exact-finite obstruction + audited meaning kernel."""
from .core import (
    STATUS_LICENSED,
    STATUS_CONDITIONAL,
    STATUS_LOCAL,
    STATUS_UNRESOLVED,
    STATUS_CONTRADICTION,
    STATUS_INVALIDATED,
    STATUS_HOLD,
    FIRST_ORDER,
    SECOND_ORDER,
    CostLedger,
    Obstruction,
)
from .engine import evaluate

__all__ = [
    "evaluate",
    "STATUS_LICENSED",
    "STATUS_CONDITIONAL",
    "STATUS_LOCAL",
    "STATUS_UNRESOLVED",
    "STATUS_CONTRADICTION",
    "STATUS_INVALIDATED",
    "STATUS_HOLD",
    "FIRST_ORDER",
    "SECOND_ORDER",
    "CostLedger",
    "Obstruction",
]
