# -*- coding: utf-8 -*-
"""把 output/ 下的 metrics.json 与图表组装为可部署的单页 HTML 报告。

用法：python3 src/build_report.py
产物：ecommerce-behavior/public/（index.html + charts/*.png）
"""
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
PUB = ROOT / "public"
(CHARTS := PUB / "charts").mkdir(parents=True, exist_ok=True)

M = json.loads((OUT / "metrics.json").read_text(encoding="utf-8"))

for png in OUT.glob("*.png"):
    shutil.copy(png, CHARTS / png.name)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def metric_card(v, label, note=""):
    return f'<div class="kpi"><b>{v}</b><span>{label}</span><em>{note}</em></div>'


seg_rows = "".join(
    f"<tr><td>{esc(s['segment'])}</td><td>{s['人数占比']}%</td><td>{s['GMV占比']}%</td>"
    f"<td>£{s['人均消费']:,.0f}</td><td>{s['人均订单']}</td></tr>"
    for s in M["segments"]
)
km_rows = "".join(
    f"<tr><td>簇 {s['cluster']}</td><td>{s['人数']:,}</td><td>{s['R均']:.0f} 天</td>"
    f"<td>{s['F均']:.1f} 次</td><td>£{s['M均']:,.0f}</td></tr>"
    for s in M["kmeans_summary"]
)
top_rows = "".join(
    f"<tr><td>{i + 1}</td><td>{esc(p['name'])}</td><td>£{p['gmv']:,.0f}</td></tr>"
    for i, p in enumerate(M["top_products"][:5])
)

seg0 = M["segments"][0]
seg_last = M["segments"][-1]

kpi = (
    metric_card(f"{M['n_customers']:,}", "活跃客户", f"{M['n_invoices']:,} 张订单")
    + metric_card(f"£{M['gmv_total'] / 1e4:.0f}万", "总销售额", f"{M['date_min']} ~ {M['date_max']}")
    + metric_card(f"£{M['aov']:.0f}", "客单价", "单张发票平均金额")
    + metric_card(f"{M['avg_monthly_repeat_rate']}%", "月均老客占比", "B2B 强复购属性")
)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>电商用户行为分析 · 数据分析报告</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%230E7A5F'/><text x='50' y='68' font-size='46' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'>电</text></svg>">
<style>
:root {{ --bg:#F5F8F7; --card:#fff; --text:#1C2B26; --muted:#7C8B85; --border:#E2EAE7; --accent:#0E7A5F; }}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif; background:var(--bg); color:var(--text); line-height:1.75; }}
header {{ background:linear-gradient(135deg,#0E7A5F,#14977A); color:#fff; padding:26px 22px 20px; border-radius:0 0 22px 22px; }}
header h1 {{ font-size:22px; }} header p {{ font-size:13px; opacity:.9; }}
main {{ max-width:900px; margin:0 auto; padding:18px 16px 50px; }}
.kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-top:-6px; }}
@media (max-width:640px) {{ .kpis {{ grid-template-columns:repeat(2,1fr); }} }}
.kpi {{ background:var(--card); border-radius:14px; box-shadow:0 2px 10px rgba(28,43,38,.07); padding:14px 10px; text-align:center; margin-top:14px; }}
.kpi b {{ display:block; font-size:22px; color:var(--accent); }}
.kpi span {{ font-size:12px; font-weight:700; }} .kpi em {{ display:block; font-size:11px; font-style:normal; color:var(--muted); }}
section {{ margin-top:22px; }}
.card {{ background:var(--card); border-radius:14px; box-shadow:0 2px 10px rgba(28,43,38,.07); padding:18px 20px; margin-top:12px; }}
h2 {{ font-size:17px; border-left:4px solid var(--accent); padding-left:10px; }}
h3 {{ font-size:15px; margin:14px 0 6px; }}
p {{ font-size:14px; margin-top:8px; }}
ul {{ font-size:14px; padding-left:20px; }} li {{ margin-top:4px; }}
img {{ max-width:100%; border-radius:10px; border:1px solid var(--border); margin-top:10px; }}
.figcap {{ font-size:12px; color:var(--muted); margin-top:4px; }}
table.tbl {{ width:100%; border-collapse:collapse; font-size:13px; margin-top:8px; }}
.tbl th, .tbl td {{ border-bottom:1px solid var(--border); padding:7px 10px; text-align:left; }}
.tbl th {{ color:var(--muted); font-weight:600; }}
.note {{ background:#EDF7F3; border:1px solid #CFE8DE; border-radius:10px; padding:10px 14px; font-size:13px; margin-top:10px; }}
.steps {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }}
.step {{ background:#E7F4F0; color:var(--accent); border-radius:999px; padding:5px 13px; font-size:12.5px; font-weight:600; }}
footer {{ text-align:center; font-size:12px; color:var(--muted); padding:26px 0 34px; }}
a {{ color:var(--accent); }}
</style>
</head>
<body>
<header>
  <h1>电商用户行为分析：RFM 分层与复购洞察</h1>
  <p>基于 UCI「Online Retail」真实交易数据集（英国线上批发商，{M['date_min']} ~ {M['date_max']}）· Python 完整流水线</p>
</header>
<main>

<div class="kpis">{kpi}</div>

<section>
  <h2>1 · 业务问题与数据</h2>
  <div class="card">
    <p>电商运营的核心问题：<b>谁是最有价值的客户？他们在什么时间买？谁正在流失？</b>本项目使用 UCI 公开数据集（{M['rows_total']:,} 行交易记录、{M['n_customers']:,} 名客户、{M['n_products']:,} 个商品、38 个国家）。</p>
    <p>流程：<span class="steps"><span class="step">数据清洗</span><span class="step">KPI 总览</span><span class="step">时段规律</span><span class="step">RFM 分层</span><span class="step">K-Means 聚类</span><span class="step">复购留存</span><span class="step">退货分析</span></span></p>
    <p>清洗动作：退货/取消单（负数量与 C 开头发票，{M['return_rate_rows']}% 行）单独分析不入销售口径；单价 ≤ 0 的调整行剔除；CustomerID 缺失的 {M['rows_no_customerid_pct']}% 订单（游客/批量单）不参与客户级分析——这一步让 RFM 的样本口径清晰可解释。</p>
  </div>
</section>

<section>
  <h2>2 · 经营节奏：月度趋势与下单时段</h2>
  <div class="card">
    <img src="charts/01_monthly_gmv.png" alt="月度GMV">
    <img src="charts/02_hour_heatmap.png" alt="时段热力">
    <p class="figcap">图1 · 月度 GMV；图2 · 星期 × 小时下单热力</p>
    <p><b>结论：</b>① 峰值月在 {M['peak_month']}（圣诞备货季），9-11 月持续走旺；② 下单集中发生在<b>工作日上午 10-12 点</b>——这是 B2B 客户在办公时间采购的典型特征；③ 该平台周六不营业，周日单量极少，运营排期与客服排班应据此对齐。</p>
  </div>
</section>

<section>
  <h2>3 · RFM 分层：谁在贡献 GMV</h2>
  <div class="card">
    <img src="charts/03_rfm_segments.png" alt="RFM分层">
    <p class="figcap">图3 · RFM 客户分层（R/F/M 各按五分位打分，映射为业务分层）</p>
    <table class="tbl">
      <thead><tr><th>分层</th><th>人数占比</th><th>GMV 占比</th><th>人均消费</th><th>人均订单</th></tr></thead>
      <tbody>{seg_rows}</tbody>
    </table>
    <p><b>结论：</b>「{esc(seg0['segment'])}」以 {seg0['人数占比']}% 的人数贡献了 {seg0['GMV占比']}% 的 GMV——显著的二八效应；而「{esc(seg_last['segment'])}」占 {seg_last['人数占比']}% 人数却只贡献 {seg_last['GMV占比']}%。运营含义：资源应向价值客户的留存与流失客户的召回两端集中，中间层的维护优先级最低。</p>
  </div>
</section>

<section>
  <h2>4 · K-Means 聚类：数据驱动的分群验证</h2>
  <div class="card">
    <img src="charts/04_kmeans.png" alt="KMeans">
    <p class="figcap">图4 · 肘部法则选 k=4；右图为 F-M 视图的聚类结果（对 R、logF、logM 标准化后聚类）</p>
    <table class="tbl">
      <thead><tr><th>簇</th><th>人数</th><th>平均 R</th><th>平均 F</th><th>平均 M</th></tr></thead>
      <tbody>{km_rows}</tbody>
    </table>
    <p><b>结论：</b>无监督聚类独立于 RFM 规则，也分离出了「高频高额核心客群（F≈16、M≈£10,000）」与「高 R 低频流失客群（R≈259 天）」，与 RFM 分层相互印证。两套方法的交叉一致性，说明分层结论不是打分规则的人为产物。</p>
  </div>
</section>

<section>
  <h2>5 · 复购结构与热门商品</h2>
  <div class="card">
    <img src="charts/05_repeat.png" alt="复购">
    <img src="charts/06_products_countries.png" alt="Top商品与地域">
    <p class="figcap">图5 · 月度老客占比；图6 · Top 畅销商品与海外市场</p>
    <p><b>结论：</b>① 月均 {M['avg_monthly_repeat_rate']}% 的当月买家是老客——这是 B2B 批发（复购驱动）而非 C 端零售（拉新驱动）的结构性证据，营销预算应偏向留存与客单提升；② 英国本土贡献 {M['uk_gmv_share']}% GMV，海外市场（荷兰、爱尔兰等）是第二增长曲线；③ 退货/取消占行数 {M['return_rate_rows']}%、占金额约 {M['return_gmv_rate']}%，属正常区间。</p>
    <table class="tbl">
      <thead><tr><th>#</th><th>Top 畅销商品</th><th>GMV</th></tr></thead>
      <tbody>{top_rows}</tbody>
    </table>
  </div>
</section>

<section>
  <h2>6 · Cohort 留存矩阵与购物篮关联</h2>
  <div class="card">
    <img src="charts/07_cohort.png" alt="Cohort留存">
    <p><b>Cohort 留存：</b>按首购月份分组的月度留存矩阵显示，首月留存平均约 {M['cohort']['avg_m1_retention']}%——B2B 客户一旦建立采购关系，粘性极强且长期稳定，这与「老客占比 70.6%」互相印证。运营含义：新客首月的转化动作（首单优惠、客服跟进）是全生命周期价值的关键杠杆。</p>
    <img src="charts/08_basket.png" alt="购物篮">
    <p><b>购物篮分析：</b>在 {M['basket']['n_popular_items']} 个高频商品（≥{M['basket']['min_freq']} 张发票）中两两计算共现提升度（lift），展示关联最强的组合。lift &gt; 1 表示两商品被同时采购的频率显著高于随机——B2B 场景下通常是「成套采购」模式，可用于组合定价与捆绑推荐；同时这类共现关系也是缺货预警的输入（A 缺货会连带 B 的订单）。</p>
    <table class="tbl">
      <thead><tr><th>商品 A</th><th>商品 B</th><th>共现发票数</th><th>lift</th></tr></thead>
      <tbody>{''.join(f"<tr><td>{esc(p['a'])}</td><td>{esc(p['b'])}</td><td>{p['co']}</td><td>{p['lift']}x</td></tr>" for p in M['basket']['top_pairs'])}</tbody>
    </table>
  </div>
</section>

<section>
  <h2>7 · 分析局限（诚实声明）</h2>
  <div class="card">
    <ul>
      <li>CustomerID 缺失的 {M['rows_no_customerid_pct']}% 订单未纳入客户级分析，RFM 口径为「可识别客户」，总 GMV 会略低于全量口径。</li>
      <li>该数据集为 B2B 批发场景，结论（如复购率 70%）不可直接外推到 C 端电商。</li>
      <li>数据无购物车/浏览事件，无法做「浏览→加购→购买」漏斗分析；RFM 的 R 以数据集末尾为基准，非真实"今天"。</li>
      <li>2011-12 只含 9 天数据，月度趋势图已标注截断，不参与环比判断。</li>
      <li>可改进方向：引入 Basket 级购物篮分析（关联规则）、对流失客户做召回 A/B 实验、用生存分析建模客户生命周期。</li>
    </ul>
  </div>
</section>

<footer>
  数据来源：<a href="https://archive.ics.uci.edu/dataset/352/online+retail" target="_blank" rel="noopener">UCI Online Retail</a> ·
  Chen, Sain &amp; Guo (2012) · 分析代码见项目仓库
 · <a href="/">← 返回作品集主页</a></footer>
</main>
</body>
</html>"""

(PUB / "index.html").write_text(html, encoding="utf-8")
print(f"报告已生成: {PUB / 'index.html'}")
