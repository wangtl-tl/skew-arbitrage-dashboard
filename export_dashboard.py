# -*- coding: utf-8 -*-
"""
偏度仪表盘快照导出器 (稳健版)。
本地偏度监控的 /api/skew/overview 是"滚动刷新子集", 不同时刻返回的品种数波动很大
(实测 51 -> 11 -> 18)。为避免把残缺数据推到公开页, 本脚本轮询多次, 取品种数最多的
那份作为当日最完整快照, 再抓取各品种详情, 合成 data.json。

每日由定时任务调用, 生成后 git push 即更新外网页面。
依赖: requests  (项目 .venv 已含)
用法: .venv/Scripts/python.exe export_dashboard.py
"""
import json
import os
import time
import datetime
import requests

BASE = os.environ.get("SKEW_MONITOR_BASE", "http://localhost:18080")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
TIMEOUT = 25
POLL_ATTEMPTS = 30     # 轮询上限(防止无限等待)
POLL_INTERVAL = 10     # 每次间隔(秒)
PLATEAU = 2            # 连续 N 次不增长即视为到达峰值, 停止轮询
EARLY_STOP = 50        # 达到该数量提前结束(已较完整)
MIN_PUSH = 10          # 低于此品种数视为监控异常, 不写入(保留上次好数据)


def get(path):
    r = requests.get(BASE + path, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def fetch_best_overview():
    """轮询多次, 监测品种数变化: 连续 PLATEAU 次不增长即认为到达本轮刷新峰值,
    返回峰值时刻的 overview (品种数最多)。"""
    best = None
    best_n = -1
    prev = -1
    stable = 0
    for i in range(POLL_ATTEMPTS):
        try:
            ov = get("/api/skew/overview")
            n = len(ov.get("products", []) or [])
            print("  轮询 #%d: 品种 %d (total=%s)" % (i + 1, n, ov.get("total")))
            if n > best_n:
                best = ov
                best_n = n
            if n >= EARLY_STOP:
                print("  已达较完整状态, 停止轮询")
                break
            if n <= prev:
                stable += 1
            else:
                stable = 0
            prev = n
            if stable >= PLATEAU:
                print("  品种数已平台期(峰值 %d), 停止轮询" % best_n)
                break
        except Exception as e:
            print("  轮询 #%d 失败: %s" % (i + 1, e))
        if i < POLL_ATTEMPTS - 1:
            time.sleep(POLL_INTERVAL)
    return best


def main():
    ov = fetch_best_overview()
    if not ov:
        raise SystemExit("无法获取监控数据, 退出(保留上次快照)")
    products = ov.get("products", []) or []
    if len(products) < MIN_PUSH:
        raise SystemExit("品种数 %d < %d, 疑似监控异常, 不覆盖上次快照" %
                         (len(products), MIN_PUSH))

    details = {}
    ok = 0
    for p in products:
        code = p.get("product")
        if not code:
            continue
        try:
            d = get("/api/skew/detail?symbol=" + str(code))
            details[code] = d
            ok += 1
        except Exception as e:
            print("  [warn] 详情抓取失败 %s: %s" % (code, e))

    out = {
        "meta": {
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "last_refresh": ov.get("last_refresh"),
            "data_delay_minutes": ov.get("data_delay_minutes"),
            "source": "本地偏度监控快照 (localhost:18080)",
            "note": "每日自动更新 (轮询取最完整快照)",
            "product_count": len(products),
        },
        "products": products,
        "signal_count": ov.get("signal_count"),
        "total": ov.get("total"),
        "details": details,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    sz = os.path.getsize(OUT) / 1024.0 / 1024.0
    print("data.json 写入完成: 品种 %d, 详情 %d/%d, 大小 %.2f MB" %
          (len(products), ok, len(products), sz))


if __name__ == "__main__":
    main()
