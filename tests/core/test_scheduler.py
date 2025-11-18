import datetime as dt
from typing import Optional

import pytest

from bullet_trade.core.scheduler import (
    generate_daily_schedule,
    get_market_periods,
    run_daily,
    run_monthly,
    run_weekly,
    unschedule_all,
)


@pytest.fixture(autouse=True)
def reset_scheduler():
    unschedule_all()
    yield
    unschedule_all()


def _build_schedule(day: dt.datetime, previous_day: Optional[dt.date] = None):
    periods = get_market_periods()
    return generate_daily_schedule(day, previous_day, periods)


def test_daily_open_minus_offset():
    run_daily(lambda ctx: None, "open-30m")
    trade_day = dt.datetime(2024, 6, 12)
    schedule = _build_schedule(trade_day)
    expected_dt = dt.datetime(2024, 6, 12, 9, 0)
    assert expected_dt in schedule


def test_daily_close_plus_seconds():
    run_daily(lambda ctx: None, "close+30s")
    trade_day = dt.datetime(2024, 6, 12)
    schedule = _build_schedule(trade_day)
    expected_dt = dt.datetime(2024, 6, 12, 15, 0, 30)
    assert expected_dt in schedule


def test_daily_explicit_time():
    run_daily(lambda ctx: None, "10:00:00")
    trade_day = dt.datetime(2024, 6, 12)
    schedule = _build_schedule(trade_day)
    expected_dt = dt.datetime(2024, 6, 12, 10, 0, 0)
    assert expected_dt in schedule


def test_daily_every_minute_range():
    run_daily(lambda ctx: None, "every_minute")
    trade_day = dt.datetime(2024, 6, 12)
    schedule = _build_schedule(trade_day)
    minute_points = [
        dt for dt, tasks in schedule.items()
        if any(task.time == "every_minute" for task in tasks)
    ]
    assert minute_points[0].time() == dt.time(9, 30)
    assert minute_points[-1].time() == dt.time(14, 59)
    assert len(minute_points) == 240  # 120 分钟 * 2 个交易时段


def test_invalid_expression_rejected():
    with pytest.raises(ValueError):
        run_daily(lambda ctx: None, "not-a-valid-time")


def test_weekly_open_offset_only_on_target_weekday():
    run_weekly(lambda ctx: None, weekday=2, time="open-30m")  # 周三
    wednesday = dt.datetime(2024, 6, 12)  # 周三
    tuesday = dt.datetime(2024, 6, 11)    # 周二

    schedule_wed = _build_schedule(wednesday)
    schedule_tue = _build_schedule(tuesday)

    expected_dt = dt.datetime(2024, 6, 12, 9, 0)
    assert expected_dt in schedule_wed
    assert dt.datetime(2024, 6, 11, 9, 0) not in schedule_tue


def test_monthly_close_offset_rolls_forward_for_holiday():
    run_monthly(lambda ctx: None, monthday=15, time="close+1h")
    # 2024-06-17 是周一，15日为周六，应该顺延到 17 日
    trade_day = dt.datetime(2024, 6, 17)
    previous_trade_day = dt.date(2024, 6, 14)
    schedule = _build_schedule(trade_day, previous_trade_day)
    expected = dt.datetime(2024, 6, 17, 16, 0)
    assert expected in schedule
