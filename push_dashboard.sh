#!/usr/bin/env bash
# 偏度仪表盘每日推送: 抓取本地监控最完整快照 -> 生成 data.json -> (有变化才)提交并推送到 GitHub Pages
# 设计: 导出被跳过(监控异常/数据不足)时正常退出, 不报错, 保留上次好数据。
#
# ── [2026-09-24 修复三处] ──────────────────────────────────────────────
# 1) `git add -A` -> 白名单暂存:
#    根因: 本自动化的 cwd 就设在 deploy_pages, WorkBuddy 会把「自动化记忆」写到
#    <cwd>/.workbuddy/ 下, 原来被 add -A 一并提交 → 自 2026-08-09 起泄露到公开仓库。
#    现改为只暂存站点产物, 并配 .gitignore 兜底。
# 2) push 加 `-c credential.helper=`:
#    仓库 credential.helper=helper-selector 会让远端操作长时间挂起(实测同一条
#    ls-remote 挂了 12 分 38 秒) → 提交永远推不出去, 2026-09-03~09-24 积压 13 个。
# 3) push 失败不再静默: 打印领先提交数并以非零退出, 让上游自动化看得见。
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

# 只暂存站点产物本身(白名单), 绝不使用 git add -A
TRACKED="data.json index.html README.md build_static.py export_dashboard.py push_dashboard.sh .gitignore"
for f in $TRACKED; do
  if [ -e "$f" ]; then
    git add -- "$f"
  fi
done

git commit -q -m "snapshot $(date +%F_%H%M)"

# 推送重试: 容错瞬时网络故障; -c credential.helper= 绕过会挂起的凭据助手; timeout 兜底防死等
BRANCH=$(git rev-parse --abbrev-ref HEAD)
for attempt in 1 2 3; do
  if timeout 120 git -c credential.helper= push -q origin "$BRANCH"; then
    echo "推送完成: $(git rev-parse --short HEAD)"
    exit 0
  fi
  echo "  push 失败(第 $attempt 次), 5s 后重试..."
  sleep 5
done

AHEAD=$(git rev-list --count "origin/$BRANCH..HEAD" 2>/dev/null || echo "?")
echo "!!! 推送失败: 已达最大重试次数 —— 本地领先 origin/$BRANCH 共 $AHEAD 个提交, 线上仪表盘将停留在旧数据 !!!"
exit 1
