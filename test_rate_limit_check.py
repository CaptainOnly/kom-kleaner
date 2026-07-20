import datetime

import pytest

from rate_limit_check import rate_limit_check


def test_no_limit_hit():
    seconds, message = rate_limit_check("600,30000", "10,200", now=datetime.datetime.now(datetime.UTC))
    assert seconds == None
    assert message is None


def test_15_minute_limit_at_0_minutes():
    seconds, message = rate_limit_check("600,30000", "600,200", now=datetime.datetime(2024, 1, 1, 0, 0, 0))
    assert seconds > 15 * 60
    assert seconds < 16 * 60
    assert "15" in message


def test_15_minute_limit_at_1_minutes():
    seconds, message = rate_limit_check("600,30000", "600,200", now=datetime.datetime(2024, 1, 1, 0, 1, 0))
    assert seconds > 14 * 60
    assert seconds < 15 * 60
    assert "15" in message


def test_15_minute_limit_at_15_minutes():
    seconds, message = rate_limit_check("600,30000", "600,200", now=datetime.datetime(2024, 1, 1, 0, 15, 0))
    assert seconds > 15 * 60
    assert seconds < 16 * 60
    assert "15" in message


def test_15_minute_limit_at_16_minutes():
    seconds, message = rate_limit_check("600,30000", "600,200", now=datetime.datetime(2024, 1, 1, 0, 16, 0))
    assert seconds > 14 * 60
    assert seconds < 15 * 60
    assert "15" in message


def test_15_minute_limit_at_30_minutes():
    seconds, message = rate_limit_check("600,30000", "600,200", now=datetime.datetime(2024, 1, 1, 0, 30, 0))
    assert seconds > 15 * 60
    assert seconds < 16 * 60
    assert "15" in message


def test_15_minute_limit_at_31_minutes():
    seconds, message = rate_limit_check("600,30000", "600,200", now=datetime.datetime(2024, 1, 1, 0, 31, 0))
    assert seconds > 14 * 60
    assert seconds < 15 * 60
    assert "15" in message


def test_15_minute_limit_at_45_minutes():
    seconds, message = rate_limit_check("600,30000", "600,200", now=datetime.datetime(2024, 1, 1, 0, 45, 0))
    assert seconds > 15 * 60
    assert seconds < 16 * 60
    assert "15" in message


def test_15_minute_limit_at_46_minutes():
    seconds, message = rate_limit_check("600,30000", "600,200", now=datetime.datetime(2024, 1, 1, 0, 46, 0))
    assert seconds > 14 * 60
    assert seconds < 15 * 60
    assert "15" in message


def test_15_minute_limit_crosses_day():
    seconds, message = rate_limit_check("600,30000", "600,200", now=datetime.datetime(2024, 1, 1, 23, 46, 0))
    assert seconds > 14 * 60
    assert seconds < 15 * 60
    assert "15" in message


def test_15_minute_limit_crosses_month():
    seconds, message = rate_limit_check("600,30000", "600,200", now=datetime.datetime(2024, 1, 31, 23, 46, 0))
    assert seconds > 14 * 60
    assert seconds < 15 * 60
    assert "15" in message


def test_15_minute_limit_crosses_year():
    seconds, message = rate_limit_check("600,30000", "600,200", now=datetime.datetime(2024, 12, 31, 23, 46, 0))
    assert seconds > 14 * 60
    assert seconds < 15 * 60
    assert "15" in message


def test_daily_limit_hit():
    seconds, message = rate_limit_check("600,30000", "300,30000", now=datetime.datetime(2024, 1, 1, 0, 0, 0))
    assert seconds > 24 * 60 * 60
    assert seconds < 24 * 60 * 60 + 60
    assert "Daily" in message


def test_daily_limit_crosses_month():
    seconds, message = rate_limit_check("600,30000", "300,30000", now=datetime.datetime(2024, 1, 31, 0, 0, 0))
    assert seconds > 24 * 60 * 60
    assert seconds < 24 * 60 * 60 + 60
    assert "Daily" in message


def test_daily_limit_crosses_year():
    seconds, message = rate_limit_check("600,30000", "300,30000", now=datetime.datetime(2024, 12, 31, 0, 0, 0))
    assert seconds > 24 * 60 * 60
    assert seconds < 24 * 60 * 60 + 60
    assert "Daily" in message
