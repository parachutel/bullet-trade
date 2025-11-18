# 回测引擎

一站式说明如何配置数据源、编写兼容聚宽的策略，并用 CLI 跑出可落盘的回测结果/报告。

## 环境与安装

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e bullet-trade[dev]
cp env.backtest.example .env
```

数据源通用变量（写入 `.env`）：

```bash
# 数据源类型 (jqdata, tushare, qmt)
DEFAULT_DATA_PROVIDER=jqdata

# 聚宽配置
JQDATA_USERNAME=your_username
JQDATA_PASSWORD=your_password
JQDATA_CACHE_DIR=~/.bullet-trade/cache/jq_cache/

# 本地 MiniQMT
MINIQMT_AUTO_DOWNLOAD=true
MINIQMT_CACHE_DIR=~/.bullet-trade/cache/miniqmt_cache
QMT_ACCOUNT_ID=1234567890
QMT_ACCOUNT_TYPE=stock

# 远程 QMT server
QMT_SERVER_HOST=10.0.0.8
QMT_SERVER_PORT=58620
QMT_SERVER_TOKEN=secret

# Tushare（可选）
# DEFAULT_DATA_PROVIDER=tushare
TUSHARE_TOKEN=your_token
TUSHARE_CACHE_DIR=~/.bullet-trade/cache/tushare_cache
```

## 推荐设置：真实价格 + 分红送股

在策略初始化中开启真实价格撮合，更贴近实盘：

```python
set_option('use_real_price', True)
```

选择真实价格成交后，系统会自动处理分红、配股等现金/股份变动。

![分红配股](assets/分红配股.png)

## 兼容聚宽的策略示例

```python
from jqdata import *

def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    g.target = ['000001.XSHE', '600000.XSHG']
    run_daily(rebalance, time='10:00')

def market_open(context):
    for stock in g.target:
        df = get_price(stock, count=5, fields=['close'])
        if df['close'][-1] > df['close'].mean():
            order_target_value(stock, 10000)
```

## 使用 CLI 运行回测

```bash
bullet-trade backtest strategies/demo_strategy.py \
  --start 2024-01-01 --end 2024-06-30 \
  --benchmark 000300.XSHG \
  --cash 100000 \
  --output backtest_results/demo
```

常用开关：

| 功能 | 参数 | 默认 | 说明 |
| --- | --- | --- | --- |
| 日志落盘 | `--log PATH` / `--no-logs` | 写入 `<output>/backtest.log` | 关闭落盘用 `--no-logs` |
| PNG 图表 | `--images` | 关闭 | 开启净值/持仓图 |
| CSV 导出 | `--no-csv` | 开启 | 禁用 CSV 时传 `--no-csv` |
| HTML 报告 | `--no-html` | 开启 | 禁用 HTML 时传 `--no-html` |

分钟级回测请确认数据源支持分钟线，并在策略里保持 `use_real_price=True`。

## 回测结果与报告

- 结果目录包含日志、CSV、HTML 报告；如需单独生成报告可执行：
  ```bash
  bullet-trade report --input backtest_results/demo --format html
  ```
- 报告文件（HTML/PNG）可直接复用到站点或 MR 截图。

![backtest_result](assets/backtest_result.png)

## 常见问题

- **中文字体**：首次生成图片会自动配置中文字体，确保系统存在任意中文字体即可。
- **数据认证失败**：检查 `.env` 中的账号/Token 或环境变量覆盖。
- **日志为空**：若未指定 `--log` 且又使用了 `--no-logs`，不会写入文件。
