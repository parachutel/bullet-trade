# QMT 远程服务（bullet-trade server）操作指南

本指南覆盖：
- 启动本地 QMT 远程服务（数据/交易）
- 使用远程服务做回测（仅数据）
- 使用远程服务驱动实盘（数据+交易）
- 聚宽环境调用远程服务（查询现金/持仓、下单/撤单）
- 开发/测试用的 stub 服务（不依赖 QMT/xtquant）

---

## 1. 前置条件

- Windows 上已安装 QMT 并能正常登录，xtquant Python 依赖已就绪（仅真实 QMT 服务需要）。
- 本机或服务器开放一个监听端口供远程访问（默认 58620）。
- 使用令牌鉴权（`--token` 或 `QMT_SERVER_TOKEN`）。建议同时配置 `--allowlist` 或 TLS 证书。

---

## 2. 启动远程服务（服务端）

最简启动（真实 QMT）：
```bash
bullet-trade server \
  --server-type=qmt \
  --listen 0.0.0.0 --port 58620 \
  --token 123456
```

常用参数：
- `--enable-data/--disable-data`：启用/禁用数据服务（默认启用）
- `--enable-broker/--disable-broker`：启用/禁用券商服务（默认启用）
- `--allowlist "10.0.0.0/8,192.168.0.0/16,127.0.0.1"`：限制访问来源 IP
- `--tls-cert FILE --tls-key FILE`：开启 TLS（强烈建议在公网使用）
- `--accounts "main=55001234:stock:C:\\Qmt\\userdata_mini"`：多账户声明（别名=账号:类型:数据目录）
- `--sub-accounts "demo@main:limit=1000000"`：虚拟子账户 + 单笔额度限制（单位：成交金额）

也可通过环境变量配置（参考 `bullet-trade/env.live.example`）：
- `QMT_ACCOUNT_ID`、`QMT_ACCOUNT_TYPE`、`QMT_DATA_PATH`、`QMT_SESSION_ID`、`QMT_AUTO_SUBSCRIBE`
- `QMT_SERVER_{LISTEN,PORT,TOKEN,ALLOWLIST,MAX_CONNECTIONS,MAX_SUBSCRIPTIONS}`
- `QMT_SERVER_ACCOUNTS`（等价 `--accounts`），`QMT_SERVER_SUB_ACCOUNTS`（等价 `--sub-accounts`）

启动日志会打印账户概览（对齐 print_portfolio_info 风格）：
```
QMT 连接建立: account_id=55001234, type=stock
📊 券商账户概览: 总资产 1,234,567.89, 可用资金 234,567.89, 仓位 81.00%
+------------+--------+------+------+--------+--------+-----------+--------+--------+------+
| 股票代码   | 名称   | 持仓 | 可用 | 成本价 | 现价   | 市值      | 盈亏   | 盈亏%  | 占比% |
+============+========+======+======+========+========+===========+========+========+======+
| 000001.XSHE| 平安银 | 1000 | 1000 | 12.345 | 13.210 | 13,210.00 | 865.00 | 7.01%  | 1.07% |
+------------+--------+------+------+--------+--------+-----------+--------+--------+------+
...
```

> 无 QMT/xtquant 环境，可用 stub 服务做联调：`bullet-trade server --server-type=stub --listen 127.0.0.1 --port 58630 --token stub`。

即时打印账户概览（远程调试）：

- 客户端请求：`action = "admin.print_account"`，payload 可选 `{ "account_key": "main", "sub_account_id": "demo@main", "limit": 8 }`
- 服务端效果：在日志中打印账户概览表格，同时返回 `{ "dtype": "text", "value": "...表格文本..." }`

---

## 3. 远程回测（仅用数据）

让回测直接走远程数据服务（不依赖本地 JQ/Tushare）：

方式 A：环境变量（推荐）
```bash
export DEFAULT_DATA_PROVIDER=qmt-remote
export QMT_SERVER_HOST=127.0.0.1
export QMT_SERVER_PORT=58620
export QMT_SERVER_TOKEN=123456

# 指定 .env 文件（可选）：
# Linux/macOS
export BT_ENV_FILE=/path/to/client.env
# Windows (PowerShell)
$env:BT_ENV_FILE = 'C:\\path\\to\\client.env'

# 运行你的回测
bullet-trade backtest strategies/my_strategy.py --start 2023-01-01 --end 2023-12-31
```

方式 B：代码内切换 Provider
```python
from bullet_trade.data.api import set_data_provider, get_price

set_data_provider('qmt-remote', host='127.0.0.1', port=58620, token='123456')
df = get_price('000001.XSHE', start_date='2023-01-01', end_date='2023-03-01', frequency='1d')
print(df.tail())
```

> 注意：远程数据由 MiniQMT 驱动，需提前准备 `QMT_DATA_PATH` 的本地数据目录（或启用自动下载）。

---

## 4. 远程实盘（数据+交易）

目标：本地/云端运行 bullet-trade LiveEngine，通过远程 QMT 服务下单。

环境变量：
```bash
export DEFAULT_DATA_PROVIDER=qmt-remote
export DEFAULT_BROKER=qmt-remote

export QMT_SERVER_HOST=127.0.0.1
export QMT_SERVER_PORT=58620
export QMT_SERVER_TOKEN=123456

# 如服务端使用了多账户/子账户，可指定：
export QMT_SERVER_ACCOUNT_KEY=main
export QMT_SERVER_SUB_ACCOUNT=demo@main
```

运行：
```bash
bullet-trade live strategies/live_order_showcase.py --broker qmt-remote
```

LiveEngine 内部会：
- 通过 `RemoteQmtProvider` 订阅行情、获取历史数据；
- 通过 `RemoteQmtBroker` 下单/撤单，并定期同步账户与持仓；
- 控制台按 `print_portfolio_info` 风格打印实时账户概览。

---

### 4.1 本地 `.env` 示例

根目录执行 `cp env.example .env` 后，可在 `bullet-trade/.env` 中追加下列参数，便于测试脚本和 CLI 统一读取：

```
DEFAULT_DATA_PROVIDER=qmt-remote
DEFAULT_BROKER=qmt-remote

QMT_SERVER_HOST=127.0.0.1
QMT_SERVER_PORT=58620
QMT_SERVER_TOKEN=123456
QMT_SERVER_ACCOUNT_KEY=main        # 可选，如服务端启用多账户
QMT_SERVER_SUB_ACCOUNT=demo@main   # 可选，指定子账户
QMT_SERVER_TLS_CERT=/path/to/ca.pem  # 可选，若启用了 TLS

# 日志相关（可选）
QMT_SERVER_LOG_FILE=/var/log/qmt-server.log
QMT_SERVER_ACCESS_LOG=1          # 是否输出 access log（默认开启）
QMT_SERVER_LOG_ACCOUNT=0         # 是否将 admin.print_account 结果写入日志，默认 0 代表不打印
```

所有 `bullet-trade` 组件（包括本次新增的远程测试）都会优先读取 `.env`，因此不再需要在每个命令前手动 `export`。

---

### 4.2 远程端到端测试（可选）

若需直接连接到你部署在公网/内网的 QMT server，并验证账户、持仓以及两种下单方式，可在 `.env` 中额外添加：

```
REMOTE_QMT_TEST_ENABLED=1
REMOTE_QMT_TEST_LIMIT_SYMBOL=000001.XSHE
REMOTE_QMT_TEST_LIMIT_PRICE=10.0
REMOTE_QMT_TEST_LIMIT_AMOUNT=100
REMOTE_QMT_TEST_MARKET_SYMBOL=000002.XSHE
REMOTE_QMT_TEST_MARKET_AMOUNT=100
REMOTE_QMT_TEST_ACCOUNT=remote-e2e
```

然后执行 `pytest tests/test_remote_broker_e2e.py -m requires_network`，该用例会：
- 读取 `QMT_SERVER_*` 参数建立远程连接；
- 获取资产与持仓；
- 同时发送一笔限价单和一笔市价单（金额可在 `.env` 中调小）；
- 通过 `get_order_status`/`sync_orders` 分别验证异步/同步订单接口；
- 撤销限价单，避免对真实账户造成持仓残留。

> 强烈建议在仿真账户或低风险环境执行此测试，并在跑完后人工确认订单状态。

---

## 5. 聚宽（JoinQuant）环境调用远程服务

步骤：复制 `helpers/bullet_trade_jq_remote_helper.py` 到聚宽研究环境；在策略中：

```python
from bullet_trade_jq_remote_helper import (
    configure, get_data_client, get_broker_client,
    order, order_value, order_target, order_target_value,
    cancel_order, get_order_status, get_open_orders,
)

# 初始化连接
configure(host='你的公网IP或域名', token='123456', port=58620)

# 1) 数据：
dc = get_data_client()
df = dc.get_price('000001.XSHE', start='2023-01-01', end='2023-02-01', frequency='1d')
print(df.tail())

# 2) 券商账户：
bc = get_broker_client()
acct = bc.get_account()  # 返回 RemoteAccount(available_cash, total_value)
positions = bc.get_positions()
print('现金:', acct.available_cash, '总资产:', acct.total_value)
for p in positions:
    print(p)

# 3) 下单/撤单：
order = bc.place_order('000001.XSHE', side='BUY', amount=100, price=10.0)
print('下单返回:', order)
status = bc.get_order_status(order.order_id)
print('状态:', status)
bc.cancel_order(order.order_id)

# 4) 聚宽风格快捷方法（含自动补价、市价转限价、同步等待）：
oid = order('000001.XSHE', 100, price=None, wait_timeout=10)
cancel_order(oid)
```

> 短连接模式（适配聚宽）的 tick 推送不可用，但下单/撤单/查询均可使用。

---

## 6. 开发与测试建议

1) 无 QMT 环境先用 stub 自测：
```bash
bullet-trade server --server-type=stub --listen 127.0.0.1 --port 58630 --token stub

# 客户端（回测/实盘都行）
export DEFAULT_DATA_PROVIDER=qmt-remote
export DEFAULT_BROKER=qmt-remote
export QMT_SERVER_HOST=127.0.0.1
export QMT_SERVER_PORT=58630
export QMT_SERVER_TOKEN=stub
```

2) 仅数据联调（不动真实账户）：
```bash
bullet-trade server --server-type=qmt --enable-data --disable-broker \
  --listen 0.0.0.0 --port 58620 --token 123456
```

3) 端到端（数据+交易）：
```bash
bullet-trade server --server-type=qmt --enable-data --enable-broker \
  --listen 0.0.0.0 --port 58620 --token 123456 \
  --accounts "main=55001234:stock:C:\\Qmt\\userdata_mini"
```

4) 多账户与子账户额度：
```bash
bullet-trade server --server-type=qmt \
  --accounts "main=55001234:stock:C:\\Qmt\\user_a,hedge=55004321:stock:C:\\Qmt\\user_b" \
  --sub-accounts "research@main:limit=200000,qa@hedge"
```

5) 安全加固：
- 非公网环境最少也启用 `--allowlist`；
- 公网务必配 `--tls-cert/--tls-key` 并限制来源 IP；
- 定期更换 `--token`。

---

## 7. 常见问题

- 日志显示现金/总资产为 0：
  - 初次连接后 QMT 刷新需要短暂时间，服务端已加入轻微等待；
  - 请确认已登录正确资金账号，且 `QMT_DATA_PATH` 指向对应数据目录；
  - xtquant 版本字段差异较大，已做多字段兼容与兜底估算（现金+持仓市值）。

- 无法下单/撤单：
  - 核对服务端是否启用券商模块（未 `--disable-broker`）；
  - 检查 `QMT_SERVER_TOKEN`、IP 白名单、TLS 配置；
  - 查看服务端日志是否有 xtquant 错误码或权限限制。

- 聚宽调用失败：
  - 请确保研究环境能访问你的服务器 IP/端口；
  - 若使用 TLS，需要同时传入 `tls_cert` 并确保可用。

---

## 8. 相关文件

- 服务端适配：`bullet_trade/server/adapters/qmt.py`
- 远程数据 Provider：`bullet_trade/data/providers/remote_qmt.py`
- 远程券商 Broker：`bullet_trade/broker/qmt_remote.py`
- 聚宽短连接客户端：`helpers/jq_remote_qmt.py`
- 启动 CLI：`bullet_trade/server/cli.py`
- 指定 .env 文件：
  - 通过环境变量覆盖：`BT_ENV_FILE=/path/to/server.env bullet-trade server ...`
  - 或命令行：`bullet-trade server --env-file /path/to/server.env ...`（会覆盖默认加载）
