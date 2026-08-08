#!/usr/bin/env bash
# 偏度仪表盘每日推送: 抓取本地监控最完整快照 -> 生成 data.json -> (有变化才)提交并推送到 GitHub Pages
# 设计: 导出被跳过(监控异常/数据不足)时正常退出, 不报错, 保留上次好数据。
set -e
cd "$(dirname "$0")"

VENV="/c/Users/DELL/WorkBuddy/偏度套利/.venv/Scripts/python.exe"
echo "[$(date +%F_%T)] 导出偏度快照 ..."
if ! "$VENV" export_dashboard.py; then
  echo "导出被跳过(监控异常或数据不足), 不推送, 保留上次快照"
  exit 0
fi

if git diff --quiet data.json; then
  echo "data.json 无变化, 跳过提交"
  exit 0
fi

git add -A
git commit -q -m "snapshot $(date +%F_%H%M)"

# 推送重试(容错瞬时网络故障), 最多 3 次
for attempt in 1 2 3; do
  if git push -q; then
    echo "推送完成: $(git rev-parse --short HEAD)"
    exit 0
  fi
  echo "  push 失败(第 $attempt 次), 5s 后重试..."
  sleep 5
done
echo "推送失败: 已达最大重试次数"
exit 1
