# 偏度套利仪表盘 (公开快照)

商品期权偏度套利信号总览的**公开静态镜像**，部署在 GitHub Pages。

- 外网地址: https://wangtl-tl.github.io/skew-arbitrage-dashboard/
- 数据源: 本地偏度监控 (http://localhost:18080)
- 更新方式: 每日自动抓取本地监控最新数据 → 生成 `data.json` → 推送到本仓库，Pages 自动刷新。

## 文件说明
- `index.html` — 偏度仪表盘页面（由 `build_static.py` 从 `templates/index.html` 改造，读 `data.json`）
- `data.json` — 每日数据快照（总览 + 各品种详情）
- `build_static.py` — 从项目模板重新生成 `index.html`
- `export_dashboard.py` — 从本地监控抓取数据生成 `data.json`

## 本地操作
```bash
# 重新生成页面(模板有改动时)
.venv/Scripts/python.exe build_static.py

# 抓取最新数据
.venv/Scripts/python.exe export_dashboard.py

# 推送
git add -A && git commit -m "snapshot $(date +%F_%H%M)" && git push
```

页面每 30 秒自动重新拉取 `data.json`，打开即见最新快照。
