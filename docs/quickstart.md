# 扩展能力：数据与交易

此页对应 bullettrade.cn 首页“扩展能力/数据与交易”入口，说明内置的数据/交易提供者与扩展方式，帮助你在保持聚宽兼容的同时扩展新的数据源或券商。

## 现有实现概览
- 数据：`jqdata`（默认）、`qmt`/MiniQMT、`tushare`（可选安装对应依赖）、本地缓存与开发中的 stub 数据源；可通过 `.env` 中的 `DEFAULT_DATA_PROVIDER` 切换。
- 券商：`qmt`（本地）、`qmt-remote`（远程服务）、`simulator`（模拟券商）可按场景选择。
- 兼容层工具（来自 `from jqdata import *`）：`get_price`、`get_trade_days`、`order_target_value`、`print_portfolio_info` 等均已对齐聚宽习惯。

## 数据提供者扩展路径

1) 继承接口：在 `bullet_trade/data/providers/base.py` 里 `DataProvider` 定义了 `get_price/get_trade_days/get_all_securities/get_index_stocks/get_split_dividend` 等必须实现的方法。  
2) 最小骨架：
   ```python
   from bullet_trade.data.providers.base import DataProvider

   class MyProvider(DataProvider):
       name = "myprovider"
       requires_live_data = False

       def auth(self, user=None, pwd=None, host=None, port=None):
           ...

       def get_price(self, security, start_date=None, end_date=None, frequency='daily', **kwargs):
           ...
       # 其他接口同上
   ```
3) 注册与使用：在策略中调用 `set_data_provider('myprovider', instance=MyProvider())`，或在 `.env` 设置 `DEFAULT_DATA_PROVIDER=myprovider`。确保 `get_price` 支持前复权/分钟线，便于回测与实盘共用。

## 交易提供者扩展路径

1) 继承接口：`bullet_trade/broker/base.py` 的 `BrokerBase` 规定了 `connect/disconnect/get_account_info/get_positions/buy/sell/cancel_order/get_order_status` 等接口（部分为异步）。  
2) 推荐实践：
   - 在 `connect` 阶段完成鉴权和会话保持，失败时抛出清晰的异常信息。
   - `buy/sell` 建议支持 `wait_timeout`，便于调用侧控制同步/异步。
   - `get_positions`/`get_account_info` 返回结构最好对齐 `RemoteBrokerClient`/QMT，包含 `security/amount/avg_cost/market_value` 等字段。
3) 注册：在 CLI 启动或策略中创建实例后，将其挂载到 engine/broker 管理处（参考现有 QMT 实现）。

## 调试与快速校验

- 回测验证：配置 `.env` 并运行 `bullet-trade backtest ...`，观察日志格式与成交记录；`LOG_DIR` 可自定义。
- 远程链路：使用 `bullet-trade server --server-type=stub` 先验证 RPC 与数据格式，再切换到真实 QMT 服务。
- 测试入口：若仅需快速回归核心逻辑，执行 `pytest -m "not slow and not requires_network"`。

## 进一步参考

- 申请补充的 API 或适配需求，请在 [API 文档](api.md) 查找导出函数，或在 Issue/PR 中描述场景。
- 如需新增实验性数据源/券商，建议先提供最小实现和使用示例，再补充自动化用例。
