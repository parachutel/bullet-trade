"""
订单系统

提供各种下单函数
"""

from dataclasses import dataclass
from typing import Optional, Union
from datetime import datetime
import uuid

from .models import Order, OrderStatus, OrderStyle
from .globals import log
from .settings import get_settings
from .runtime import process_orders_now


# 全局订单队列
_order_queue = []


@dataclass
class MarketOrderStyle:
    """市价单参数，可指定保护价或买卖价差。"""
    limit_price: Optional[float] = None
    buy_price_percent: Optional[float] = None
    sell_price_percent: Optional[float] = None


@dataclass
class LimitOrderStyle:
    """限价单参数：显式给出委托价格。"""
    price: float


def _generate_order_id() -> str:
    """生成唯一订单ID"""
    return str(uuid.uuid4())


def order(
    security: str,
    amount: int,
    price: Optional[float] = None,
    style: Optional[Union[OrderStyle, MarketOrderStyle, LimitOrderStyle]] = None,
    wait_timeout: Optional[float] = None,
) -> Optional[Order]:
    """
    按股数下单
    
    Args:
        security: 标的代码
        amount: 股数，正数表示买入，负数表示卖出
        price: 委托价格，None表示市价单
        style: 下单方式或市价参数（策略覆写）
        
    Returns:
        Order对象，如果下单失败返回None
    """
    if isinstance(price, (MarketOrderStyle, LimitOrderStyle)):
        style = price
        price = None

    if amount == 0:
        log.warning(f"下单数量为0，忽略订单: {security}")
        return None
    
    if price is not None:
        resolved_style: object = LimitOrderStyle(price)
    else:
        resolved_style = style if style is not None else MarketOrderStyle()

    order_obj = Order(
        order_id=_generate_order_id(),
        security=security,
        amount=abs(amount),
        price=price if price is not None else 0.0,
        status=OrderStatus.open,
        add_time=datetime.now(),
        is_buy=(amount > 0),
        style=resolved_style,
        wait_timeout=wait_timeout,
    )
    
    _order_queue.append(order_obj)
    log.debug(f"创建订单: {security}, 数量: {amount}, 价格: {price}")
    # 即时撮合：与聚宽保持一致的行为
    try:
        settings = get_settings()
        if settings.options.get('order_match_mode') == 'immediate':
            process_orders_now()
    except Exception as e:
        log.warning(f"即时撮合失败，保留到队列: {e}")
    
    return order_obj


def order_value(
    security: str,
    value: float,
    price: Optional[float] = None,
    style: Optional[Union[OrderStyle, MarketOrderStyle, LimitOrderStyle]] = None,
    wait_timeout: Optional[float] = None,
) -> Optional[Order]:
    """
    按价值下单
    
    Args:
        security: 标的代码
        value: 目标价值，正数表示买入，负数表示卖出
        price: 委托价格，None表示市价单
        
    Returns:
        Order对象，如果下单失败返回None
        
    Note:
        实际数量会在撮合时根据当前价格计算
    """
    if isinstance(price, (MarketOrderStyle, LimitOrderStyle)):
        style = price
        price = None

    if value == 0:
        log.warning(f"下单价值为0，忽略订单: {security}")
        return None
    
    # 临时订单，amount会在撮合时计算
    if price is not None:
        resolved_style: object = LimitOrderStyle(price)
    else:
        resolved_style = style if style is not None else MarketOrderStyle()

    order_obj = Order(
        order_id=_generate_order_id(),
        security=security,
        amount=0,  # 会在撮合时计算
        price=price if price is not None else 0.0,
        status=OrderStatus.open,
        add_time=datetime.now(),
        is_buy=(value > 0),
        style=resolved_style,
        wait_timeout=wait_timeout,
    )
    
    # 存储目标价值，用于撮合时计算
    order_obj._target_value = abs(value)  # type: ignore
    
    _order_queue.append(order_obj)
    log.debug(f"创建订单（按价值）: {security}, 价值: {value}")
    try:
        settings = get_settings()
        if settings.options.get('order_match_mode') == 'immediate':
            process_orders_now()
    except Exception as e:
        log.warning(f"即时撮合失败，保留到队列: {e}")
    
    return order_obj


def order_target(
    security: str,
    amount: int,
    price: Optional[float] = None,
    style: Optional[Union[OrderStyle, MarketOrderStyle, LimitOrderStyle]] = None,
    wait_timeout: Optional[float] = None,
) -> Optional[Order]:
    """
    目标股数下单（调整持仓到目标数量）
    """
    if isinstance(price, (MarketOrderStyle, LimitOrderStyle)):
        style = price
        price = None

    if price is not None:
        resolved_style: object = LimitOrderStyle(price)
    else:
        resolved_style = style if style is not None else MarketOrderStyle()

    order_obj = Order(
        order_id=_generate_order_id(),
        security=security,
        amount=abs(amount),
        price=price if price is not None else 0.0,
        status=OrderStatus.open,
        add_time=datetime.now(),
        is_buy=True,
        style=resolved_style,
        wait_timeout=wait_timeout,
    )

    order_obj._is_target_amount = True  # type: ignore
    order_obj._target_amount = amount  # type: ignore

    _order_queue.append(order_obj)
    log.debug(f"创建订单（目标股数）: {security}, 目标数量: {amount}")
    try:
        settings = get_settings()
        if settings.options.get('order_match_mode') == 'immediate':
            process_orders_now()
    except Exception as e:
        log.warning(f"即时撮合失败，保留到队列: {e}")

    return order_obj


def order_target_value(
    security: str,
    value: float,
    price: Optional[float] = None,
    style: Optional[Union[OrderStyle, MarketOrderStyle, LimitOrderStyle]] = None,
    wait_timeout: Optional[float] = None,
) -> Optional[Order]:
    """
    目标价值下单（调整持仓到目标价值）
    """
    if isinstance(price, (MarketOrderStyle, LimitOrderStyle)):
        style = price
        price = None

    if price is not None:
        resolved_style: object = LimitOrderStyle(price)
    else:
        resolved_style = style if style is not None else MarketOrderStyle()

    order_obj = Order(
        order_id=_generate_order_id(),
        security=security,
        amount=0,
        price=price if price is not None else 0.0,
        status=OrderStatus.open,
        add_time=datetime.now(),
        is_buy=True,
        style=resolved_style,
        wait_timeout=wait_timeout,
    )

    order_obj._is_target_value = True  # type: ignore
    order_obj._target_value = value  # type: ignore

    _order_queue.append(order_obj)
    log.debug(f"创建订单（目标价值）: {security}, 目标价值 {value}")
    try:
        settings = get_settings()
        if settings.options.get('order_match_mode') == 'immediate':
            process_orders_now()
    except Exception as e:
        log.warning(f"即时撮合失败，保留到队列: {e}")

    return order_obj


def get_order_queue():
    """获取当前订单队列"""
    return _order_queue


def clear_order_queue():
    """清空订单队列"""
    global _order_queue
    _order_queue = []


__all__ = [
    'order',
    'order_value',
    'order_target',
    'order_target_value',
    'get_order_queue',
    'clear_order_queue',
    'MarketOrderStyle',
    'LimitOrderStyle',
]
