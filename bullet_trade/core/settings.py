"""
策略设置函数

提供各种策略配置功能
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class OrderCost:
    """
    交易费用设置
    
    Attributes:
        open_tax: 买入印花税
        close_tax: 卖出印花税
        open_commission: 买入佣金
        close_commission: 卖出佣金
        min_commission: 最小佣金
        close_today_commission: 平今佣金（期货用）
    """
    open_tax: float = 0.0
    close_tax: float = 0.001  # 卖出印花税默认千分之一
    open_commission: float = 0.0003  # 买入佣金默认万三
    close_commission: float = 0.0003  # 卖出佣金默认万三
    min_commission: float = 5.0  # 最小佣金5元
    close_today_commission: float = 0.0
    
    def calculate_tax(self, amount: float, is_buy: bool) -> float:
        """
        计算印花税
        
        Args:
            amount: 交易金额
            is_buy: 是否买入
            
        Returns:
            印花税金额
        """
        if is_buy:
            return amount * self.open_tax
        else:
            return amount * self.close_tax
    
    def calculate_commission(self, amount: float, is_buy: bool) -> float:
        """
        计算佣金
        
        Args:
            amount: 交易金额
            is_buy: 是否买入
            
        Returns:
            佣金金额
        """
        if is_buy:
            commission = amount * self.open_commission
        else:
            commission = amount * self.close_commission
        
        return max(commission, self.min_commission)


def _default_order_costs() -> Dict[str, OrderCost]:
    """返回各资产类别的默认费用配置。"""
    return {
        'stock': OrderCost(
            open_tax=0.0,
            close_tax=0.001,
            open_commission=0.0003,
            close_commission=0.0003,
            min_commission=5.0,
        ),
        'fund': OrderCost(
            open_tax=0.0,
            close_tax=0.0,
            open_commission=0.0003,
            close_commission=0.0003,
            min_commission=5.0,
        ),
        'money_market_fund': OrderCost(
            open_tax=0.0,
            close_tax=0.0,
            open_commission=0.0,
            close_commission=0.0,
            min_commission=0.0,
        ),
    }


@dataclass
class FixedSlippage:
    """
    固定滑点
    
    Attributes:
        value: 滑点值（如0.0003表示万分之三）
    """
    value: float = 0.0
    
    def calculate_slippage(self, price: float, is_buy: bool) -> float:
        """
        计算滑点后的价格
        
        Args:
            price: 原始价格
            is_buy: 是否买入
            
        Returns:
            滑点后的价格
        """
        # 模拟价差的一半落到单边（行业通用写法）：
        # 例如设置 0.00246，则买入 +0.00123，卖出 -0.00123
        half = self.value / 2.0
        if is_buy:
            return price * (1 + half)
        else:
            return price * (1 - half)


class StrategySettings:
    """策略设置管理器"""
    
    def __init__(self):
        self.benchmark: Optional[str] = None  # 基准
        self.order_cost: Dict[str, OrderCost] = _default_order_costs()  # 不同类型的交易费用
        self.slippage: Optional[FixedSlippage] = None  # 滑点
        self.options: Dict[str, Any] = {
            'use_real_price': False,  # 是否使用真实价格（动态复权）
            'avoid_future_data': False,  # 是否避免未来数据
            'order_volume_ratio': 0.25,  # 成交量比例
            'order_match_mode': 'immediate',  # 下单撮合模式：'bar_end' 或 'immediate'
            'match_by_signal': False,  # 限价资金检查按信号价或撮合价
        }
    
    def reset(self):
        """重置所有设置"""
        self.benchmark = None
        self.order_cost = _default_order_costs()
        self.slippage = None
        self.options = {
            'use_real_price': False,
            'avoid_future_data': False,
            'order_volume_ratio': 0.25,
            'order_match_mode': 'immediate',
            'match_by_signal': False,
        }


# 全局设置实例
_settings = StrategySettings()


def set_benchmark(security: str):
    """
    设置基准
    
    Args:
        security: 基准标的代码，如 '000300.XSHG'（沪深300）
    """
    _settings.benchmark = security


def set_order_cost(order_cost: OrderCost, type: str = 'stock'):
    """
    设置交易费用
    
    Args:
        order_cost: OrderCost对象
        type: 交易类型（'stock', 'fund', 'futures'等）
    """
    _settings.order_cost[type] = order_cost


def set_slippage(slippage: FixedSlippage):
    """
    设置滑点
    
    Args:
        slippage: FixedSlippage对象
    """
    _settings.slippage = slippage


def set_option(key: str, value: Any):
    """
    设置选项
    
    Args:
        key: 选项名称
            - 'use_real_price': 是否使用真实价格（动态复权）
            - 'avoid_future_data': 是否避免未来数据
            - 'order_volume_ratio': 成交量比例
            - 'order_match_mode': 下单撮合模式（'bar_end'|'immediate'）
            - 'match_by_signal': 限价资金检查使用信号价(True)或撮合价(False)
        value: 选项值
    """
    _settings.options[key] = value


def get_settings() -> StrategySettings:
    """获取设置实例"""
    return _settings


def reset_settings():
    """重置所有设置"""
    _settings.reset()


__all__ = [
    'OrderCost', 'FixedSlippage',
    'set_benchmark', 'set_order_cost', 'set_slippage', 'set_option',
    'get_settings', 'reset_settings'
]
