"""
Journal: persist signals and trades with full rationale and rulebook reference.
Append-only; for audit and post-trade review.
"""

from journal.writer import JournalWriter

__all__ = ["JournalWriter"]
