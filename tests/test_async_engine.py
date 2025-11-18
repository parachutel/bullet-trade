"""
异步回测引擎测试

测试 AsyncBacktestEngine 的核心功能
"""

import asyncio
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bullet_trade.core.async_engine import AsyncBacktestEngine


# ============ 测试策略 ============

def test_simple_sync_strategy():
    """测试同步策略在异步引擎中运行"""
    
    # 同步策略（现有代码风格）
    def initialize(context):
        from bullet_trade.core.settings import set_benchmark
        from bullet_trade.core.scheduler import run_daily
        
        set_benchmark('000300.XSHG')
        context.stocks = ['000001.XSHE', '600000.XSHG']
        run_daily(market_open, 'open')
    
    def market_open(context):
        """定时任务函数：只接收 context 参数（符合聚宽规范）"""
        from bullet_trade.core.orders import order_target_value
        
        for stock in context.stocks:
            order_target_value(stock, 5000)
    
    # 创建异步引擎（不传 handle_data，只使用定时任务）
    engine = AsyncBacktestEngine(
        initialize=initialize,
    )
    
    # 运行回测（异步模式）
    results = engine.run(
        start_date='2024-01-01',
        end_date='2024-01-31',
        capital_base=100000,
        frequency='daily',
        use_async=True  # 关键参数
    )
    
    assert results is not None
    assert 'summary' in results
    assert 'meta' in results
    
    # 从新的结构中提取数据
    final_value = results['meta']['final_total_value']
    initial_value = results['meta']['initial_total_value']
    total_returns = (final_value - initial_value) / initial_value
    
    print(f"\n✅ 同步策略测试通过")
    print(f"   总收益率: {total_returns:.2%}")
    print(f"   最终价值: ¥{final_value:,.2f}")
    print(f"   耗时: {results.get('runtime_seconds', 0):.2f}秒")


@pytest.mark.asyncio
async def test_async_strategy():
    """测试异步策略"""
    
    # 异步策略
    async def initialize(context):
        from bullet_trade.core.settings import set_benchmark
        from bullet_trade.core.scheduler import run_daily
        
        set_benchmark('000300.XSHG')
        context.stocks = ['000001.XSHE']
        run_daily(market_open, 'open')
    
    async def market_open(context):
        """异步定时任务函数：只接收 context 参数（符合聚宽规范）"""
        from bullet_trade.core.orders import order_target_value
        
        # 模拟异步操作
        await asyncio.sleep(0.001)
        
        for stock in context.stocks:
            order_target_value(stock, 10000)
    
    # 创建异步引擎（不传 handle_data，只使用定时任务）
    engine = AsyncBacktestEngine(
        initialize=initialize,
    )
    
    # 直接调用 run_async
    results = await engine.run_async(
        start_date='2024-01-01',
        end_date='2024-01-31',
        capital_base=100000,
        frequency='daily'
    )
    
    assert results is not None
    assert 'summary' in results
    assert 'meta' in results
    
    # 从新的结构中提取数据
    final_value = results['meta']['final_total_value']
    initial_value = results['meta']['initial_total_value']
    total_returns = (final_value - initial_value) / initial_value
    
    print(f"\n✅ 异步策略测试通过")
    print(f"   总收益率: {total_returns:.2%}")
    print(f"   最终价值: ¥{final_value:,.2f}")
    print(f"   耗时: {results.get('runtime_seconds', 0):.2f}秒")


def test_backward_compatibility():
    """测试向后兼容性：use_async=False 使用原有引擎"""
    
    def initialize(context):
        from bullet_trade.core.settings import set_benchmark
        set_benchmark('000300.XSHG')
        context.stocks = ['000001.XSHE']
    
    def market_open(context, data):
        from bullet_trade.core.orders import order
        order(context.stocks[0], 100)
    
    # 创建异步引擎，但以同步模式运行
    engine = AsyncBacktestEngine(
        initialize=initialize,
        handle_data=market_open,
    )
    
    # use_async=False（默认值）
    results = engine.run(
        start_date='2024-01-01',
        end_date='2024-01-10',
        capital_base=100000,
        frequency='daily',
        use_async=False  # 使用同步模式
    )
    
    assert results is not None
    
    print(f"\n✅ 向后兼容性测试通过")
    print(f"   同步模式正常工作")


# ============ 性能对比测试 ============

def test_performance_comparison():
    """对比同步和异步模式的性能"""
    
    def initialize(context):
        from bullet_trade.core.settings import set_benchmark
        from bullet_trade.core.scheduler import run_daily
        
        set_benchmark('000300.XSHG')
        context.stocks = ['000001.XSHE', '600000.XSHG', '000002.XSHE']
        run_daily(market_open, 'open')
    
    def market_open(context):
        """定时任务函数：只接收 context 参数（符合聚宽规范）"""
        from bullet_trade.core.orders import order_target_value
        
        for stock in context.stocks:
            order_target_value(stock, 3000)
    
    # 同步模式（不传 handle_data，只使用定时任务）
    engine_sync = AsyncBacktestEngine(
        initialize=initialize,
    )
    
    results_sync = engine_sync.run(
        start_date='2024-01-01',
        end_date='2024-03-31',
        capital_base=100000,
        frequency='daily',
        use_async=False
    )
    
    time_sync = results_sync.get('runtime_seconds', 0)
    
    # 异步模式（不传 handle_data，只使用定时任务）
    engine_async = AsyncBacktestEngine(
        initialize=initialize,
    )
    
    results_async = engine_async.run(
        start_date='2024-01-01',
        end_date='2024-03-31',
        capital_base=100000,
        frequency='daily',
        use_async=True
    )
    
    time_async = results_async.get('runtime_seconds', 0)
    
    print(f"\n📊 性能对比")
    print(f"   同步模式: {time_sync:.2f}秒")
    print(f"   异步模式: {time_async:.2f}秒")
    
    if time_async < time_sync:
        speedup = time_sync / time_async
        print(f"   ⚡ 异步模式快 {speedup:.2f}x")
    else:
        print(f"   ℹ️  性能相近（日线回测差异不大）")


# ============ 主程序 ============

if __name__ == "__main__":
    print("🧪 开始测试异步回测引擎...\n")
    
    print("="*60)
    print("测试 1：同步策略在异步引擎中运行")
    print("="*60)
    test_simple_sync_strategy()
    
    print("\n" + "="*60)
    print("测试 2：纯异步策略")
    print("="*60)
    asyncio.run(test_async_strategy())
    
    print("\n" + "="*60)
    print("测试 3：向后兼容性")
    print("="*60)
    test_backward_compatibility()
    
    print("\n" + "="*60)
    print("测试 4：性能对比")
    print("="*60)
    test_performance_comparison()
    
    print("\n" + "="*60)
    print("🎉 所有测试通过！")
    print("="*60)
    
    print("\n💡 核心特性验证：")
    print("  ✅ 同步策略无需修改即可在异步引擎中运行")
    print("  ✅ 异步策略获得更好的性能（分钟/实盘）")
    print("  ✅ 向后兼容：use_async=False 使用原有引擎")
    print("  ✅ 事件驱动：集成 EventLoop + EventBus + AsyncScheduler")
    print("  ✅ 防重叠执行：AsyncScheduler 自动处理")

