# 实盘引擎

此页对应 bullettrade.cn 首页“实盘引擎”卡片，介绍本地独立实盘与远程实盘两种路径。当前支持券商：QMT（含远程服务）；未准备好真实环境时可先使用模拟券商。

## 独立实盘（本地 QMT）

开始前：在当前仓库根目录复制实盘模板到 `.env`，再按需补全券商/目录信息。
```bash
cp env.live.example .env
```

1) 在 `.env` 中准备账户与运行目录：
```bash
DEFAULT_BROKER=qmt
QMT_DATA_PATH=C:\国金QMT交易端\userdata_mini
MINIQMT_AUTO_DOWNLOAD=true
QMT_ACCOUNT_ID=123456
QMT_ACCOUNT_TYPE=stock            # 或 future
LOG_DIR=logs
RUNTIME_DIR=runtime
```
2) 保证本机 QMT/xtquant 已登录且数据目录指向正确账号。  
3) 启动策略：
```bash
bullet-trade live strategies/demo_strategy.py --broker qmt --log-dir logs/live
```
- 日志与运行时数据写入 `LOG_DIR` / `RUNTIME_DIR`，建议先用小仓位或模拟券商 `--broker simulator` 做一次 dry-run。

## 远程实盘（MiniQMT + bullet-trade server）

面向云端/局域网托管：在远程 Windows 主机运行 MiniQMT + bullet-trade server，本地仅负责编排策略。

1) 服务端（远程主机）启动：
```bash
bullet-trade server --listen 0.0.0.0 --port 58620 --token secret \
  --enable-data --enable-broker \
  --accounts main=123456:stock
```
2) 本地 `.env` 设置远程信息：
```bash
DEFAULT_BROKER=qmt-remote
QMT_SERVER_HOST=10.0.0.8
QMT_SERVER_PORT=58620
QMT_SERVER_TOKEN=secret
QMT_SERVER_ACCOUNT_KEY=main        # 多账户时指定
```
3) 连接远程实盘：
```bash
bullet-trade live strategies/demo_strategy.py --broker qmt-remote
```
- 若需先验证链路，可将远程服务以 `--server-type=stub` 方式启动，仅做联调不触达真实账户。

## 生命周期回调与代码变更
- `initialize`：仅在策略首次加载时执行一次，用于设置基准、全局变量等。
- `process_initialize`：每次实盘进程重启都会执行，适合恢复 g/状态、重建连接。
- `after_code_change`：当检测到策略代码更新并重新加载后执行一次，可用于迁移状态或打印版本号。
- 按需在回调里加载 `RUNTIME_DIR` 的 pickle 结果，避免重启后丢失上下文。

## 状态持久化与存储目录（g 的 pickle）
- 实盘运行时会定期将全局变量 `g` 与上下文做序列化（pickle），默认写入 `RUNTIME_DIR`（未设置则使用 `runtime/`）。  
- 建议在 `.env` 中显式配置 `RUNTIME_DIR` 与 `LOG_DIR`，并确保目录可写且有足够磁盘空间；目录中通常包含：
  - `runtime/state.pkl`（或类似命名）：序列化后的 `g`/context，进程重启时可加载恢复。
  - `logs/live/*.log`：实盘/远程连接日志，便于排查。
- 若在容器/集群环境运行，请将 `RUNTIME_DIR` 和 `LOG_DIR` 指向挂载卷，避免容器重建导致状态丢失。

## 安全与风控提示
- `.env` 中包含的账号与 token 不要入库；变更前重新执行一次回测/仿真对比行为。
- 策略内建议保留风控钩子：停牌过滤、最大回撤、成交失败重试等。
- 更多 QMT server 配置与日志路径，请参考 [QMT 服务配置](qmt-server.md)。

## 部署建议：性价比云主机
- 若需要低成本长期在线的远程实盘环境，可选约 99 元/年的基础款阿里云轻量服务器（2c/2G 起），安装 MiniQMT + `bullet-trade server` 后本地通过 `qmt-remote` 连接。注意：
  - 仅在合规范围内使用，确保网络与安全组开放对应端口（如 58620）且搭配 token/TLS。
  - 挂载数据盘或定期同步运行目录，避免单点宕机导致状态/日志丢失。
