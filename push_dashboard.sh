#!/usr/bin/env bash
# 偏度仪表盘每日推送: 抓取本地监控最新数据 -> 生成 data.json -> (有变化才)提交并推送到 GitHub Pages
set -e
cd "$(dirname "$0")"

VENV="/c/Users/DELL/WorkBuddy/偏度套利/.venv/Scripts/python.exe"
echo "[$(date +%F_%T)] 导出偏度快照 ..."
"$VENV" export_dashboard.py

if git diff --quiet data.json; then
  echo "data.json 无变化, 跳过提交"
  exit 0
fi

git add -A
git commit -q -m "snapshot $(date +%F_%H%M)"
git push -q
echo "推送完成: $(git rev-parse --short HEAD)"
