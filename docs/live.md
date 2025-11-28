# 实盘引擎

本页涵盖本地 QMT/模拟与远程 qmt-remote 两种运行方式，聚焦最小可用流程与关键截图。

## 场景对比（先选路径）

| 场景 | 命令 | 必填变量 | 适合谁 |
| --- | --- | --- | --- |
| 本地 QMT | `bullet-trade live ... --broker qmt` | `QMT_DATA_PATH`、`QMT_ACCOUNT_ID` | 已安装 QMT/xtquant，想直接盯盘 |
| 模拟券商 | `--broker simulator` | 无 | 风控演练/联调 |
| 远程 qmt-remote | `--broker qmt-remote` | `QMT_SERVER_HOST/PORT/TOKEN` | 云/局域网托管，策略在本地 |

> 更多变量说明见 [配置总览](config.md)。

## 实盘引擎生命周期

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         实盘引擎启动流程                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  bullet-trade live strategy.py --broker qmt                             │
│                          │                                              │
│                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  1. 加载策略文件                                                 │   │
│  │     └─ 解析 initialize / process_initialize / after_code_changed │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  2. 检查运行时状态                                               │   │
│  │     ├─ 读取 RUNTIME_DIR/live_state.json                         │   │
│  │     └─ 读取 RUNTIME_DIR/g.pkl（全局变量持久化）                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│            ┌─────────────┴─────────────┐                                │
│            ▼                           ▼                                │
│   ┌────────────────┐         ┌────────────────┐                        │
│   │  首次启动      │         │  重启/恢复     │                        │
│   │  initialize()  │         │  (跳过 init)   │                        │
│   └────────────────┘         └────────────────┘                        │
│            │                           │                                │
│            └─────────────┬─────────────┘                                │
│                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  3. process_initialize()                                         │   │
│  │     └─ 每次进程启动都会调用（适合恢复连接、订阅行情）              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  4. 连接券商                                                     │   │
│  │     ├─ 本地 QMT：连接 xtquant                                    │   │
│  │     ├─ 远程：连接 QMT Server                                     │   │
│  │     └─ 同步账户资产、持仓                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  5. 进入事件循环（等待交易时段）                                  │   │
│  │     └─ 根据 run_daily / run_weekly 调度任务                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 典型交易日时间线

```
时间          事件                              策略回调
──────────────────────────────────────────────────────────────────────────
 08:30       引擎启动/恢复                      process_initialize()
   │
 09:15       集合竞价开始                       before_trading_start()
   │
 09:30       ─── 开盘 ───                       
   │         
 09:30       执行定时任务                       run_daily(func, '09:30')
   │
 10:00       执行定时任务                       run_daily(func, '10:00')
   │
 11:30       ─── 午休 ───
   │
 13:00       ─── 下午开盘 ───
   │
 14:00       执行定时任务                       run_daily(func, '14:00')
   │
 14:55       尾盘任务                           run_daily(func, '14:55')
   │
 15:00       ─── 收盘 ───                       after_trading_end()
   │
 15:05       状态持久化                         自动保存 g.pkl / live_state.json
   │
 15:30       可选：停止引擎 / 继续等待次日
──────────────────────────────────────────────────────────────────────────
```

## 策略回调函数说明

| 回调函数 | 触发时机 | 典型用途 |
|----------|----------|----------|
| `initialize(context)` | 首次启动时调用一次 | 设置全局变量、注册定时任务 |
| `process_initialize(context)` | 每次进程启动都调用 | 恢复连接、订阅行情、加载缓存 |
| `before_trading_start(context)` | 每个交易日开盘前 | 获取当日股票池、预处理数据 |
| `after_trading_end(context)` | 每个交易日收盘后 | 统计当日盈亏、发送通知 |
| `after_code_changed(context)` | 代码热更新后 | 重新加载配置、更新参数 |
| `run_daily(func, time)` | 指定时间点 | 执行交易逻辑 |
| `run_weekly(func, weekday, time)` | 每周指定日 | 周度调仓 |

## 本地 QMT / 模拟最小步骤

```bash
cp env.live.example .env
# 核心变量（其余看 config.md）
DEFAULT_BROKER=qmt          # 或 simulator
QMT_DATA_PATH=C:\国金QMT交易端\userdata_mini
QMT_ACCOUNT_ID=123456
LOG_DIR=logs
RUNTIME_DIR=runtime

bullet-trade live strategies/demo_strategy.py --broker qmt
```
- 建议先用 `--broker simulator` dry-run，再切换真实账号。

### 实盘效果与日志

QMT 本机持仓/下单：
![qmt-trade-live](assets/qmt-trade-live.png)

委托状态（限价/市价/撤单）：
![miniqmt-limit-market-rollback](assets/miniqmt-limit-market-rollback.png)

同步下单日志（16s超时队列 vs 0.5s 成交示例）：
![sync-order](assets/sync-order.png)

运行态持久化目录（`live_state.json`、`g.pkl`）：
![run-time-dir](assets/run-time-dir.png)

## 远程实盘（qmt-remote）

1) 远程 Windows 主机启动（需放行防火墙）：
```bash
bullet-trade server --listen 0.0.0.0 --port 58620 --token secret \
  --enable-data --enable-broker \
  --accounts main=123456:stock
```
首次启动会弹防火墙，请选择放行：
![server-firewall](assets/server-firewall.png)

2) 本地 `.env`：
```bash
DEFAULT_BROKER=qmt-remote
QMT_SERVER_HOST=10.0.0.8
QMT_SERVER_PORT=58620
QMT_SERVER_TOKEN=secret
QMT_SERVER_ACCOUNT_KEY=main
```

3) 运行策略：
```bash
bullet-trade live strategies/demo_strategy.py --broker qmt-remote
```

4) 服务端日志示例：
![joinquant-server-qmt](assets/joinquant-server-qmt.png)

## 状态持久化与恢复

实盘引擎会自动保存运行状态，支持断点恢复：

```
RUNTIME_DIR/
├── live_state.json    # 引擎状态（上次运行时间、策略哈希等）
└── g.pkl              # 全局变量 g 的序列化（自动保存/恢复）
```

### 持久化流程

```
┌─────────────────────────────────────────────────────────────┐
│  运行时自动持久化                                            │
├─────────────────────────────────────────────────────────────┤
│  1. 定时保存（默认每 60 秒）                                 │
│     └─ g.pkl 序列化全局变量                                  │
│                                                             │
│  2. 收盘后保存                                              │
│     ├─ g.pkl                                                │
│     └─ live_state.json（含策略哈希、时间戳）                 │
│                                                             │
│  3. 优雅退出时保存                                          │
│     └─ Ctrl+C 或 SIGTERM 触发                               │
└─────────────────────────────────────────────────────────────┘
```

### 恢复逻辑

- **有 runtime 状态**：跳过 `initialize()`，直接调用 `process_initialize()`
- **无 runtime 状态**：正常调用 `initialize()` + `process_initialize()`
- **代码变更**：检测到策略文件哈希变化，额外调用 `after_code_changed()`

## 安全与风控

- `.env` 不入库；远程服务务必带 `--token`，必要时限制到内网。
- 策略层保留风控钩子：停牌过滤、最大回撤、成交失败重试等。
- QMT server 更多参数见 [QMT server](qmt-server.md)。
- 若要让聚宽模拟盘接入远程实盘，请看 [trade-support](trade-support.md)。

### 风控参数配置（.env）

| 变量 | 默认值 | 作用 |
| --- | --- | --- |
| `MAX_ORDER_VALUE` | `100000` | 单笔订单金额上限，超过即拒单 |
| `MAX_DAILY_TRADE_VALUE` | `500000` | 单日累计成交金额上限，超过即拒单 |
| `MAX_DAILY_TRADES` | `100` | 单日最大交易笔数，超过即拒单 |
| `MAX_STOCK_COUNT` | `20` | 持仓标的数上限（仅买入检查） |
| `MAX_POSITION_RATIO` | `20` | 单标下单金额占总资产的最大比例 |
| `STOP_LOSS_RATIO` | `5` | 止损阈值，需策略自行下撤单 |
| `RISK_CHECK_ENABLED` | `false` | 开启后台风控巡检 |

> 提示：默认值偏宽，真实账户请按资金量收紧；先用 `LIVE_MODE=dry_run` 验证风控配置，再切 `LIVE_MODE=live`。

![risk-control](assets/real-risk-control.png)

## 常见问题

### QMT 连接失败
- 检查 `QMT_DATA_PATH` 路径是否正确
- 确认 QMT 客户端已启动并登录
- 查看是否有其他程序占用 xtquant

### 远程连接超时
- 检查防火墙是否放行端口
- 确认 `QMT_SERVER_HOST` 和 `PORT` 正确
- 验证 Token 是否匹配

### 订单未成交
- 检查账户资金是否充足
- 确认标的是否停牌
- 查看风控是否拦截（日志中会有提示）

### 状态恢复失败
- 检查 `RUNTIME_DIR` 权限
- 尝试删除 `g.pkl` 重新初始化
- 查看 `live_state.json` 是否损坏
