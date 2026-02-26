"""Business day calculations for Texas real estate transactions.

Ported from TC Tracker's business-days.ts. Includes federal + Texas holidays.
"""
from __future__ import annotations

from datetime import date, timedelta


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Get the Nth weekday of a month. weekday: 0=Mon..6=Sun."""
    first = date(year, month, 1)
    days_until = (weekday - first.weekday()) % 7
    return first + timedelta(days=days_until + (n - 1) * 7)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """Get the last occurrence of a weekday in a month."""
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    days_back = (last.weekday() - weekday) % 7
    return last - timedelta(days=days_back)


def get_federal_holidays(year: int) -> set[date]:
    """Return federal holidays for the given year."""
    thanksgiving = _nth_weekday(year, 11, 3, 4)  # 4th Thursday Nov
    return {
        date(year, 1, 1),                       # New Year's Day
        _nth_weekday(year, 1, 0, 3),            # MLK Day (3rd Monday Jan)
        _nth_weekday(year, 2, 0, 3),            # Presidents' Day (3rd Monday Feb)
        _last_weekday(year, 5, 0),              # Memorial Day (last Monday May)
        date(year, 6, 19),                       # Juneteenth
        date(year, 7, 4),                        # Independence Day
        _nth_weekday(year, 9, 0, 1),            # Labor Day (1st Monday Sep)
        _nth_weekday(year, 10, 0, 2),           # Columbus Day (2nd Monday Oct)
        date(year, 11, 11),                      # Veterans Day
        thanksgiving,                            # Thanksgiving
        date(year, 12, 25),                      # Christmas Day
    }


def get_texas_holidays(year: int) -> set[date]:
    """Return Texas-specific holidays."""
    thanksgiving = _nth_weekday(year, 11, 3, 4)
    return {
        date(year, 3, 2),                        # Texas Independence Day
        date(year, 4, 21),                       # San Jacinto Day
        date(year, 8, 27),                       # LBJ Day
        thanksgiving + timedelta(days=1),        # Day After Thanksgiving
        date(year, 12, 24),                      # Christmas Eve
        date(year, 12, 26),                      # Day After Christmas
    }


def _get_all_holidays(year: int) -> set[date]:
    """Get all holidays (federal + Texas) for a year."""
    return get_federal_holidays(year) | get_texas_holidays(year)


def is_business_day(d: date) -> bool:
    """Check if a date is a business day (not weekend, not federal/Texas holiday)."""
    if d.weekday() >= 5:
        return False
    return d not in _get_all_holidays(d.year)


def add_business_days(start: date, days: int) -> date:
    """Add N business days to a date. Negative days go backward."""
    result = start
    remaining = abs(days)
    direction = 1 if days >= 0 else -1
    while remaining > 0:
        result += timedelta(days=direction)
        if is_business_day(result):
            remaining -= 1
    return result


def adjust_to_business_day(d: date) -> date:
    """If the date falls on a weekend/holiday, move to next business day."""
    while not is_business_day(d):
        d += timedelta(days=1)
    return d
