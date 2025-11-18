import datetime as dt
from typing import Iterable, Optional, Sequence

import pandas as pd
import pytest

from bullet_trade.core.engine import BacktestEngine
from bullet_trade.core.scheduler import (
    run_daily,
    run_monthly,
    run_weekly,
    unschedule_all,
)
from bullet_trade.core.settings import reset_settings, set_option


class StubProvider:
    def __init__(self, trade_days: Sequence[dt.date]):
        self._trade_days = [pd.Timestamp(day) for day in trade_days]

    def auth(self, *args, **kwargs):
        return True

    def get_price(
        self,
        security,
        start_date=None,
        end_date=None,
        frequency: str = "daily",
        fields: Optional[Iterable[str]] = None,
        count: Optional[int] = None,
        panel: bool = True,
        **kwargs,
    ) -> pd.DataFrame:
        fields = list(fields) if fields else ["close"]
        freq = "T" if frequency == "minute" else "D"
        if count:
            end = pd.to_datetime(end_date)
            dates = pd.date_range(end=end, periods=count, freq=freq)
        else:
            start = pd.to_datetime(start_date) if start_date is not None else pd.to_datetime(end_date)
            end = pd.to_datetime(end_date)
            dates = pd.date_range(start=start, end=end, freq=freq)

        if isinstance(security, (list, tuple)):
            securities = list(security)
        else:
            securities = [security]

        data = {}
        for field in fields:
            values = [100.0] * len(dates)
            if len(securities) == 1:
                data[field] = values
            else:
                for code in securities:
                    data[(field, code)] = values

        df = pd.DataFrame(data, index=dates)
        if any(isinstance(col, tuple) for col in df.columns):
            df.columns = pd.MultiIndex.from_tuples(df.columns)
        return df

    def get_trade_days(self, start_date=None, end_date=None, count=None):
        days = self._trade_days
        if start_date is not None:
            start_ts = pd.to_datetime(start_date)
            days = [d for d in days if d >= start_ts]
        if end_date is not None:
            end_ts = pd.to_datetime(end_date)
            days = [d for d in days if d <= end_ts]
        if count is not None:
            if end_date is not None:
                return days[-count:]
            return days[:count]
        return days

    def get_all_securities(self, *args, **kwargs):
        return pd.DataFrame(
            {"display_name": ["测试证券"], "start_date": ["2000-01-01"], "end_date": ["2099-12-31"]},
            index=["000001.XSHE"],
        )

    def get_index_stocks(self, *args, **kwargs):
        return ["000001.XSHE"]


@pytest.fixture(autouse=True)
def reset_state():
    unschedule_all()
    reset_settings()
    yield
    unschedule_all()
    reset_settings()


def _patch_provider(monkeypatch, trade_days: Sequence[str]):
    provider = StubProvider(trade_days)
    import bullet_trade.data.api as api_module

    monkeypatch.setattr(api_module, "_provider", provider, raising=False)
    monkeypatch.setattr(api_module, "_auth_attempted", True, raising=False)
    return provider


def test_backtest_engine_daily_time_expressions(monkeypatch):
    trade_day = "2024-06-17"
    _patch_provider(monkeypatch, [trade_day])

    timeline = {
        "before_open": [],
        "open_minus_30s": [],
        "open": [],
        "ten": [],
        "mid_close": [],
        "close_plus_30s": [],
        "close_plus_30m": [],
        "handle_data": [],
    }
    minute_info = {"count": 0, "first": None, "last": None, "mid_last": None}

    def record(tag):
        def _inner(context):
            timeline[tag].append(context.current_dt)
        return _inner

    def every_minute(context):
        minute_info["count"] += 1
        minute_info["first"] = minute_info["first"] or context.current_dt
        minute_info["last"] = context.current_dt
        if context.current_dt.time() < dt.time(12, 0):
            minute_info["mid_last"] = context.current_dt

    def initialize(context):
        set_option("use_real_price", False)
        run_daily(record("before_open"), "open-30m")
        run_daily(record("open_minus_30s"), "open-30s")
        run_daily(record("open"), "open")
        run_daily(record("ten"), "10:00:00")
        run_daily(record("mid_close"), "11:30:00")
        run_daily(record("close_plus_30s"), "close+30s")
        run_daily(record("close_plus_30m"), "close+30m")
        run_daily(every_minute, "every_minute")

    def handle_data(context, data):
        timeline["handle_data"].append(context.current_dt)

    engine = BacktestEngine(initialize=initialize, handle_data=handle_data)
    engine.run(
        start_date=trade_day,
        end_date=trade_day,
        capital_base=100000,
        frequency="daily",
    )

    assert timeline["before_open"][0].time() == dt.time(9, 0)
    assert timeline["open_minus_30s"][0].time() == dt.time(9, 29, 30)
    assert timeline["open"][0].time() == dt.time(9, 30)
    assert timeline["ten"][0].time() == dt.time(10, 0)
    assert timeline["mid_close"][0].time() == dt.time(11, 30)
    assert timeline["close_plus_30s"][0].time() == dt.time(15, 0, 30)
    assert timeline["close_plus_30m"][0].time() == dt.time(15, 30)
    assert timeline["handle_data"][0].time() == dt.time(9, 30)
    assert minute_info["count"] == 240
    assert minute_info["first"].time() == dt.time(9, 30)
    assert minute_info["last"].time() == dt.time(14, 59)
    assert minute_info["mid_last"].time() == dt.time(11, 29)


def test_backtest_engine_weekly_and_monthly(monkeypatch):
    trade_days = ["2024-06-12", "2024-06-13", "2024-06-14", "2024-06-17"]
    _patch_provider(monkeypatch, trade_days)

    weekly_hits: list[dt.datetime] = []
    monthly_hits: list[dt.datetime] = []

    def initialize(context):
        run_weekly(lambda ctx: weekly_hits.append(ctx.current_dt), weekday=2, time="open-30m")
        run_monthly(lambda ctx: monthly_hits.append(ctx.current_dt), monthday=15, time="close+1h")

    engine = BacktestEngine(initialize=initialize)
    engine.run(
        start_date=trade_days[0],
        end_date=trade_days[-1],
        capital_base=100000,
        frequency="daily",
    )

    assert [hit.date() for hit in weekly_hits] == [dt.date(2024, 6, 12)]
    assert monthly_hits == [dt.datetime(2024, 6, 17, 16, 0)]
