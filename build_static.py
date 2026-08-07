# -*- coding: utf-8 -*-
"""
从 templates/index.html 生成 GitHub Pages 用的纯静态偏度仪表盘 (index.html)。
原理: 模板本身不含 Jinja, 只是通过 /api/* 拉数据。本脚本把 4 处 fetch 改成读
同目录下的 data.json (由 export_dashboard.py 生成), 并增加"快照时间"显示。
模板保持原样不动(本地监控仍用原版)。
"""
import os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "index.html")
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

with open(SRC, "r", encoding="utf-8") as f:
    html = f.read()


def replace_once(html, old, new, label):
    n = html.count(old)
    if n != 1:
        raise SystemExit(f"[ERROR] {label}: 期望替换 1 处, 实际 {n} 处。请检查模板是否已改动。")
    return html.replace(old, new)


# A. 声明 detailsMap / META 全局
html = replace_once(
    html,
    "let currentPairKey = '';",
    "let currentPairKey = '';\nlet detailsMap = {};\nlet META = {};",
    "A-全局声明",
)

# B. fetchOverview: 去掉 /api/status, 改读 data.json, 用 meta 填状态栏
old_b = """    // 获取系统状态
    const sResp = await fetch('/api/status');
    if (sResp.ok) {
      const status = await sResp.json();
      updateStatusBar(status);
      // 首次加载中(未ready): 保持 loading spinner, 不渲染空表
      if (status.status !== 'ready' && status.total_products === 0) {
        document.getElementById('tableLoading').style.display = 'flex';
        document.getElementById('tableLoading').innerHTML =
          '<div class="loading-spinner"></div><span>首次加载中 (解析主力合约中)... ' + (status.status_message || '') + '</span>';
        document.getElementById('mainTable').style.display = 'none';
        return;
      }
    }

    // 获取偏度总览数据
    const r = await fetch('/api/skew/overview');
    if (!r.ok) throw new Error('API error: ' + r.status);
    const data = await r.json();"""
new_b = """    // [静态快照模式] 直接读取本地 data.json (由 export_dashboard.py 每日生成并推送)
    const r = await fetch('data.json');
    if (!r.ok) throw new Error('加载 data.json 失败: ' + r.status);
    const data = await r.json();
    META = data.meta || {};
    detailsMap = data.details || {};
    // 状态栏(快照模式)
    updateStatusBar({
      status: 'ready', connected: true,
      last_refresh: META.last_refresh || META.generated_at,
      total_products: (data.total != null ? data.total : (data.products||[]).length),
      signal_count: data.signal_count || 0
    });
    updateSnapshotLabel();"""
html = replace_once(html, old_b, new_b, "B-fetchOverview")

# C. openPanel: 详情从 detailsMap 读取, 不再请求 /api/skew/detail
old_c = """    const r = await fetch(`/api/skew/detail?symbol=${product}`);
    // [侧滑栏] 区分 HTTP 错误 vs 业务错误, 显示后端真实原因
    if (!r.ok) {
      let detail = '';
      try {
        const e = await r.json();
        detail = e.error || e.message || '';
      } catch (_) { detail = r.statusText; }
      throw new Error(detail || ('HTTP ' + r.status));
    }
    currentDetail = await r.json();"""
new_c = """    const detail = detailsMap[product];
    if (!detail) throw new Error('暂无该品种快照详情（可能本期未纳入）');
    currentDetail = detail;"""
html = replace_once(html, old_c, new_c, "C-openPanel")

# D. manualRefresh: 改为重新拉取 data.json
old_d = """async function manualRefresh() {
  try {
    await fetch('/api/refresh', { method: 'POST' });
    document.getElementById('statusText').textContent = '刷新已触发...';
    setTimeout(fetchOverview, 3000);
  } catch(e) {
    console.error('刷新失败:', e);
  }
}"""
new_d = """async function manualRefresh() {
  document.getElementById('statusText').textContent = '重新加载快照...';
  await fetchOverview();
}"""
html = replace_once(html, old_d, new_d, "D-manualRefresh")

# E. 状态栏: 在"延时"后插入"快照时间"
old_e = """  <div class="status-item">
    <span class="delay-tag" id="delayTag">延时约15分钟</span>
  </div>
  <div class="status-divider"></div>
  <div class="status-item">
    <span>品种: </span><strong id="totalProducts">0</strong>
  </div>"""
new_e = """  <div class="status-item">
    <span class="delay-tag" id="delayTag">延时约15分钟</span>
  </div>
  <div class="status-divider"></div>
  <div class="status-item">
    <span>快照: </span><span id="snapshotTime">—</span>
  </div>
  <div class="status-divider"></div>
  <div class="status-item">
    <span>品种: </span><strong id="totalProducts">0</strong>
  </div>"""
html = replace_once(html, old_e, new_e, "E-状态栏快照时间")

# F. 新增 updateSnapshotLabel 函数(放在 updateSignalAlert 之前)
old_f = "function updateSignalAlert(count) {"
new_f = """function updateSnapshotLabel() {
  const el = document.getElementById('snapshotTime');
  if (!el) return;
  if (META && META.generated_at) {
    try { el.textContent = new Date(META.generated_at).toLocaleString('zh-CN', {hour12:false}); }
    catch(e) { el.textContent = META.generated_at; }
  } else { el.textContent = '—'; }
}
function updateSignalAlert(count) {"""
html = replace_once(html, old_f, new_f, "F-updateSnapshotLabel")

with open(DST, "w", encoding="utf-8") as f:
    f.write(html)

print("index.html 生成成功 ->", os.path.abspath(DST))
print("剩余 /api/ 引用:", html.count("/api/"))
