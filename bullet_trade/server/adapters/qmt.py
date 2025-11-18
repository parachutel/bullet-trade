from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bullet_trade.broker.qmt import QmtBroker
from bullet_trade.data.providers.miniqmt import MiniQMTProvider
from bullet_trade.utils.env_loader import get_data_provider_config

from ..config import AccountConfig, ServerConfig
from .base import (
    AccountContext,
    AccountRouter,
    AdapterBundle,
    RemoteBrokerAdapter,
    RemoteDataAdapter,
)
from . import register_adapter


def _provider_config() -> Dict[str, Any]:
    cfg = get_data_provider_config().get("qmt", {})
    return {
        "data_dir": cfg.get("data_dir"),
        "cache_dir": cfg.get("cache_dir"),
        "market": cfg.get("market"),
        "auto_download": cfg.get("auto_download"),
        "tushare_token": cfg.get("tushare_token"),
        "mode": "live",
    }


class QmtDataAdapter(RemoteDataAdapter):
    def __init__(self) -> None:
        self.provider = MiniQMTProvider(_provider_config())

    async def get_history(self, payload: Dict) -> Dict:
        security = payload.get("security")
        count = payload.get("count")
        start = payload.get("start")
        end = payload.get("end")
        frequency = payload.get("frequency") or payload.get("period")
        fq = payload.get("fq")

        def _call():
            return self.provider.get_price(
                security,
                count=count,
                start_date=start,
                end_date=end,
                frequency=frequency,
                fq=fq,
            )

        df = await asyncio.to_thread(_call)
        return dataframe_to_payload(df)

    async def get_snapshot(self, payload: Dict) -> Dict:
        security = payload.get("security")

        def _call():
            return self.provider.get_current_tick(security)

        tick = await asyncio.to_thread(_call)
        return tick or {}

    async def get_live_current(self, payload: Dict) -> Dict:
        """返回实盘快照（含停牌标记）。"""
        security = payload.get("security")

        def _call():
            return self.provider.get_live_current(security)

        tick = await asyncio.to_thread(_call)
        return tick or {}

    async def get_trade_days(self, payload: Dict) -> Dict:
        start = payload.get("start")
        end = payload.get("end")

        def _call():
            return self.provider.get_trade_days(start_date=start, end_date=end)

        days = await asyncio.to_thread(_call)
        return {"dtype": "list", "values": [str(day) for day in days]}

    async def get_security_info(self, payload: Dict) -> Dict:
        security = payload.get("security")

        def _call():
            return self.provider.get_security_info(security)

        info = await asyncio.to_thread(_call)
        return {"dtype": "dict", "value": info or {}}

    async def ensure_cache(self, payload: Dict) -> Dict:
        security = payload.get("security")
        frequency = payload.get("frequency") or payload.get("period") or "1m"
        start = payload.get("start")
        end = payload.get("end")
        auto = bool(payload.get("auto_download", True))
        result = await asyncio.to_thread(
            self.provider.ensure_cache,
            security,
            frequency,
            start,
            end,
            auto_download=auto,
        )
        return {"dtype": "dict", "value": result or {}}

    async def get_current_tick(self, symbol: str) -> Optional[Dict]:
        return await asyncio.to_thread(self.provider.get_current_tick, symbol)

    async def get_all_securities(self, payload: Dict) -> Dict:
        types = payload.get("types") or "stock"
        date = payload.get("date")

        def _call():
            return self.provider.get_all_securities(types=types, date=date)

        df = await asyncio.to_thread(_call)
        return dataframe_to_payload(df)

    async def get_index_stocks(self, payload: Dict) -> Dict:
        index_symbol = payload.get("index_symbol")
        date = payload.get("date")

        def _call():
            return self.provider.get_index_stocks(index_symbol, date=date)

        stocks = await asyncio.to_thread(_call)
        return {"values": stocks or []}

    async def get_split_dividend(self, payload: Dict) -> Dict:
        security = payload.get("security")
        start = payload.get("start")
        end = payload.get("end")

        def _call():
            return self.provider.get_split_dividend(security, start_date=start, end_date=end)

        events = await asyncio.to_thread(_call)
        return {"events": events or []}


class QmtBrokerAdapter(RemoteBrokerAdapter):
    def __init__(self, config: ServerConfig, account_router: AccountRouter):
        self.config = config
        self.account_router = account_router
        self._brokers: Dict[str, QmtBroker] = {}

    async def start(self) -> None:
        for ctx in self.account_router.list_accounts():
            broker = QmtBroker(
                account_id=ctx.config.account_id,
                account_type=ctx.config.account_type,
                data_path=ctx.config.data_path,
                session_id=ctx.config.session_id,
                auto_subscribe=ctx.config.auto_subscribe,
            )
            await asyncio.to_thread(broker.connect)
            self._brokers[ctx.config.key] = broker
            await self.account_router.attach_handle(ctx.config.key, broker)

    async def stop(self) -> None:
        for broker in self._brokers.values():
            try:
                await asyncio.to_thread(broker.disconnect)
            except Exception:
                pass

    def _broker_for(self, ctx: AccountContext) -> QmtBroker:
        broker = self._brokers.get(ctx.config.key)
        if not broker:
            raise RuntimeError(f"account {ctx.config.key} not connected")
        return broker

    async def get_account_info(self, account: AccountContext, payload: Optional[Dict] = None) -> Dict:
        broker = self._broker_for(account)
        info = await asyncio.to_thread(broker.get_account_info)
        return {"dtype": "dict", "value": info}

    async def get_positions(self, account: AccountContext, payload: Optional[Dict] = None) -> List[Dict]:
        broker = self._broker_for(account)
        positions = await asyncio.to_thread(broker.get_positions)
        return positions or []

    async def list_orders(self, account: AccountContext, filters: Optional[Dict] = None) -> List[Dict]:
        broker = self._broker_for(account)
        getter = getattr(broker, "get_open_orders", None)
        if getter:
            orders = await asyncio.to_thread(getter)
            return orders or []
        return []

    async def get_order_status(
        self, account: AccountContext, order_id: Optional[str] = None, payload: Optional[Dict] = None
    ) -> Dict:
        if not order_id and payload:
            order_id = payload.get("order_id")
        if not order_id:
            raise ValueError("缺少 order_id")
        broker = self._broker_for(account)
        status = await broker.get_order_status(order_id)
        return status or {}

    async def place_order(self, account: AccountContext, payload: Dict) -> Dict:
        broker = self._broker_for(account)
        security = payload["security"]
        amount = int(payload.get("amount") or payload.get("volume") or 0)
        side = payload.get("side", "BUY").upper()
        style = payload.get("style") or {"type": "limit"}
        style_type = (style.get("type") or "limit").lower()
        price = style.get("price")
        market_flag = style_type == "market"
        if market_flag and price is None:
            price = style.get("protect_price") or payload.get("reference_price")
        if not market_flag and price is None:
            raise ValueError("缺少委托价格，请在 style.price 中提供")
        if side == "BUY":
            order = await broker.buy(security, amount, price, wait_timeout=payload.get("wait_timeout"), market=market_flag)
        else:
            order = await broker.sell(security, amount, price, wait_timeout=payload.get("wait_timeout"), market=market_flag)
        if isinstance(order, str):
            return {"order_id": order}
        return order or {}

    async def cancel_order(
        self, account: AccountContext, order_id: Optional[str] = None, payload: Optional[Dict] = None
    ) -> Dict:
        if not order_id and payload:
            order_id = payload.get("order_id")
        if not order_id:
            raise ValueError("缺少 order_id")
        broker = self._broker_for(account)
        result = await broker.cancel_order(order_id)
        return {"dtype": "dict", "value": result or {}}


def dataframe_to_payload(df):
    if df is None:
        return {"dtype": "dataframe", "columns": [], "records": []}
    try:
        columns = list(df.columns)
        records = df.reset_index().values.tolist() if df.index.name else df.values.tolist()
    except Exception:
        columns = getattr(df, "columns", [])
        records = getattr(df, "values", [])
    return {
        "dtype": "dataframe",
        "columns": [str(col) for col in columns],
        "records": records,
    }


def build_qmt_bundle(config: ServerConfig, router: AccountRouter) -> AdapterBundle:
    data_adapter = QmtDataAdapter() if config.enable_data else None
    broker_adapter = QmtBrokerAdapter(config, router) if config.enable_broker else None
    return AdapterBundle(data_adapter=data_adapter, broker_adapter=broker_adapter)


register_adapter("qmt", build_qmt_bundle)
