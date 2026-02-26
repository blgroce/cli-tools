"""Tests for business day calculations."""
from datetime import date

from tc.business_days import (
    is_business_day,
    add_business_days,
    adjust_to_business_day,
    get_federal_holidays,
    get_texas_holidays,
)


def test_weekday_is_business_day():
    assert is_business_day(date(2026, 3, 4)) is True  # Wednesday, no holiday


def test_saturday_not_business_day():
    assert is_business_day(date(2026, 2, 28)) is False  # Saturday


def test_sunday_not_business_day():
    assert is_business_day(date(2026, 3, 1)) is False  # Sunday


def test_christmas_not_business_day():
    assert is_business_day(date(2026, 12, 25)) is False


def test_texas_independence_day():
    # March 2, 2026 is a Monday but also Texas Independence Day
    assert is_business_day(date(2026, 3, 2)) is False


def test_add_business_days_forward():
    # Start Friday March 6, add 1 business day = Monday March 9
    result = add_business_days(date(2026, 3, 6), 1)
    assert result == date(2026, 3, 9)


def test_add_business_days_backward():
    # Start Monday March 9, subtract 1 business day = Friday March 6
    result = add_business_days(date(2026, 3, 9), -1)
    assert result == date(2026, 3, 6)


def test_adjust_saturday_to_monday():
    result = adjust_to_business_day(date(2026, 2, 28))  # Saturday
    assert result == date(2026, 3, 3)  # Next business day (Monday 3/2 is Texas Independence Day)


def test_adjust_business_day_unchanged():
    result = adjust_to_business_day(date(2026, 3, 4))  # Wednesday
    assert result == date(2026, 3, 4)


def test_federal_holidays_count():
    holidays = get_federal_holidays(2026)
    assert len(holidays) == 11


def test_texas_holidays_count():
    holidays = get_texas_holidays(2026)
    assert len(holidays) == 6


def test_thanksgiving_is_correct():
    # 2026 Thanksgiving = 4th Thursday of November = Nov 26
    holidays = get_federal_holidays(2026)
    assert date(2026, 11, 26) in holidays


def test_day_after_thanksgiving():
    holidays = get_texas_holidays(2026)
    assert date(2026, 11, 27) in holidays
