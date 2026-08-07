# -*- coding: utf-8 -*-
"""
偏度仪表盘快照导出器。
从本地运行的偏度监控 (默认 http://localhost:18080) 抓取总览 + 每个品种详情,
合成 GitHub Pages 用的 data.json (含 meta/products/details)。
每日由定时任务调用, 生成后 git push 即更新外网页面。

依赖: requests  (项目 .venv 已含)
用法: .venv/Scripts/python.exe export_dashboard.py
"""
import json
import os
import datetime
import requests

BASE = os.environ.get("SKEW_MONITOR_BASE", "http://localhost:18080")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
TIMEOUT = 25


def get(path):
    r = requests.get(BASE + path, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def main():
    ov = get("/api/skew/overview")
    products = ov.get("products", []) or []
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
            "note": "每日自动更新",
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
