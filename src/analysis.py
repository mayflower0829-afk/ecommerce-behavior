# -*- coding: utf-8 -*-
"""电商用户行为分析 — 完整分析流水线

数据：UCI "Online Retail"（英国电商 2010-12 ~ 2011-12 真实交易，54万行）
流程：清洗 → KPI 总览 → 时段规律 → RFM 分层（分位打分 + K-Means）→ 复购留存 → 退货分析 → 输出报告资产
输出：output/ 图表 PNG 与 metrics.json
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti TC", "Arial Unicode MS", "STHeiti"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 130
C = {"main": "#0E7A5F", "warm": "#D97706", "bad": "#E5484D", "grey": "#9AA5B1"}

metrics = {}

# ========== 1. 清洗 ==========
df = pd.read_excel(ROOT / "data" / "Online_Retail.xlsx")
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
df["Revenue"] = df["Quantity"] * df["UnitPrice"]
df["InvoiceNoStr"] = df["InvoiceNo"].astype(str)

n0 = len(df)
cancelled = df["InvoiceNoStr"].str.startswith("C")
negative_qty = df["Quantity"] <= 0
returns = df[negative_qty | cancelled]                      # 退货/取消单独分析
sales = df[~negative_qty & ~cancelled & (df["UnitPrice"] > 0)].copy()

known = sales[sales["CustomerID"].notna()].copy()           # RFM 需要客户标识
metrics["rows_total"] = int(n0)
metrics["rows_return_or_cancel"] = int((negative_qty | cancelled).sum())
metrics["return_rate_rows"] = round(float((negative_qty | cancelled).mean()) * 100, 2)
metrics["rows_no_customerid_pct"] = round(float(sales["CustomerID"].isna().mean()) * 100, 1)
metrics["gmv_total"] = round(float(known["Revenue"].sum()), 0)
metrics["n_customers"] = int(known["CustomerID"].nunique())
metrics["n_invoices"] = int(known["InvoiceNoStr"].nunique())
metrics["n_products"] = int(known["StockCode"].nunique())
metrics["aov"] = round(float(known.groupby("InvoiceNoStr")["Revenue"].sum().mean()), 1)
metrics["date_min"] = str(df["InvoiceDate"].min().date())
metrics["date_max"] = str(df["InvoiceDate"].max().date())

# ========== 2. 月度 GMV 趋势 ==========
known["ym"] = known["InvoiceDate"].dt.to_period("M").astype(str)
monthly = known.groupby("ym")["Revenue"].sum()
fig, ax = plt.subplots(figsize=(9, 3.6))
ax.plot(monthly.index, monthly.values / 1e4, marker="o", color=C["main"], lw=2)
ax.set_ylabel("月销售额（万英镑）")
ax.set_title("月度 GMV：9-11 月为旺季，12 月仅含 9 天数据（截断）")
ax.tick_params(axis="x", rotation=45)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "01_monthly_gmv.png", bbox_inches="tight")
plt.close(fig)
metrics["peak_month"] = str(monthly.idxmax())
metrics["peak_month_gmv"] = round(float(monthly.max()), 0)

# ========== 3. 下单时段规律（星期 × 小时热力） ==========
known["dow"] = known["InvoiceDate"].dt.dayofweek
known["hour"] = known["InvoiceDate"].dt.hour
# reindex 到完整 7 天：该平台周六无交易，缺失会让后续标签整体错位
heat = (known.pivot_table(index="dow", columns="hour", values="Revenue", aggfunc="sum")
        .reindex(range(7)).fillna(0))
fig, ax = plt.subplots(figsize=(10, 3.8))
im = ax.imshow(np.log1p(heat), aspect="auto", cmap="Greens")
ax.set_yticks(range(7), ["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
ax.set_xlabel("下单小时")
ax.set_title("下单时段热力（颜色 = ln(销售额)）：工作日上午 10-12 点为峰值；该平台周六不营业")
fig.colorbar(im, ax=ax, shrink=0.85)
fig.tight_layout()
fig.savefig(OUT / "02_hour_heatmap.png", bbox_inches="tight")
plt.close(fig)

# ========== 4. RFM 与 K-Means 分层 ==========
SNAP = known["InvoiceDate"].max() + pd.Timedelta(days=1)
rfm = known.groupby("CustomerID").agg(
    R=("InvoiceDate", lambda s: (SNAP - s.max()).days),
    F=("InvoiceNoStr", "nunique"),
    M=("Revenue", "sum"),
)
metrics["rfm_n"] = int(len(rfm))

# 4a. 分位打分（业务语言分层）
rfm["R_s"] = pd.qcut(rfm["R"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
rfm["F_s"] = pd.qcut(rfm["F"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["M_s"] = pd.qcut(rfm["M"], 5, labels=[1, 2, 3, 4, 5]).astype(int)


def segment(row):
    if row["R_s"] >= 4 and row["F_s"] >= 4:
        return "重要价值客户"
    if row["R_s"] >= 4:
        return "重要发展客户"
    if row["F_s"] >= 4:
        return "重要保持客户"
    if row["R_s"] <= 2 and row["F_s"] <= 2:
        return "流失客户"
    return "一般客户"


rfm["segment"] = rfm.apply(segment, axis=1)
seg_stat = rfm.groupby("segment").agg(
    人数=("M", "size"), 人均消费=("M", "mean"), 人均订单=("F", "mean")
).round(1)
seg_stat["人数占比"] = (seg_stat["人数"] / len(rfm) * 100).round(1)
seg_stat["GMV占比"] = (rfm.groupby("segment")["M"].sum() / metrics["gmv_total"] * 100).round(1)
seg_stat = seg_stat.sort_values("GMV占比", ascending=False)
metrics["segments"] = seg_stat.reset_index().to_dict("records")

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
colors = [C["main"], "#14977A", C["warm"], C["bad"], C["grey"], "#64748B"][: len(seg_stat)]
axes[0].bar(seg_stat.index, seg_stat["人数占比"], color=colors)
for i, v in enumerate(seg_stat["人数占比"]):
    axes[0].text(i, v + 0.6, f"{v:.0f}%", ha="center", fontsize=9)
axes[0].set_ylabel("人数占比 %")
axes[0].set_title("RFM 客户分层：人数占比")
axes[0].tick_params(axis="x", rotation=15)
axes[0].spines[["top", "right"]].set_visible(False)
axes[1].bar(seg_stat.index, seg_stat["GMV占比"], color=colors)
for i, v in enumerate(seg_stat["GMV占比"]):
    axes[1].text(i, v + 0.6, f"{v:.0f}%", ha="center", fontsize=9)
axes[1].set_ylabel("GMV 占比 %")
axes[1].set_title("RFM 客户分层：消费贡献")
axes[1].tick_params(axis="x", rotation=15)
axes[1].spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "03_rfm_segments.png", bbox_inches="tight")
plt.close(fig)

# 4b. K-Means（对 log 变换后的 R/F/M 聚类，肘部法则选 k）
X = np.column_stack([rfm["R"], np.log1p(rfm["F"]), np.log1p(rfm["M"])])
Xs = StandardScaler().fit_transform(X)
inertias = [KMeans(n_clusters=k, random_state=42, n_init=10).fit(Xs).inertia_ for k in range(2, 9)]
K_SEL = 4
km = KMeans(n_clusters=K_SEL, random_state=42, n_init=10).fit(Xs)
rfm["cluster"] = km.labels_
cl = rfm.groupby("cluster").agg(人数=("M", "size"), R均=("R", "mean"), F均=("F", "mean"),
                                M均=("M", "mean")).round(1)
metrics["kmeans_summary"] = cl.reset_index().to_dict("records")

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].plot(range(2, 9), inertias, marker="o", color=C["main"])
axes[0].set_xlabel("聚类数 k")
axes[0].set_ylabel("簇内平方和（惯性）")
axes[0].set_title(f"肘部法则（选择 k={K_SEL}）")
axes[0].spines[["top", "right"]].set_visible(False)
for c in range(K_SEL):
    sub = rfm[rfm["cluster"] == c]
    axes[1].scatter(sub["F"], sub["M"] / 1e4, s=8, alpha=0.4, label=f"簇{c}(n={len(sub)})")
axes[1].set_xlabel("购买频次 F")
axes[1].set_ylabel("消费金额（千英镑）")
axes[1].set_title("K-Means 聚类结果（F-M 视图， ylim 截断至 2 万）")
axes[1].set_ylim(0, 20)
axes[1].legend(fontsize=8)
axes[1].spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "04_kmeans.png", bbox_inches="tight")
plt.close(fig)

# ========== 5. 复购与留存 ==========
cust_month = known.groupby("CustomerID")["ym"].apply(set)
months_all = sorted(known["ym"].unique())
repeat_rate_by_month = []
for m in months_all:
    prev = known[known["ym"] < m]["CustomerID"].unique()
    cur = set(known[known["ym"] == m]["CustomerID"].unique())
    if len(prev) == 0:
        continue
    repeat_rate_by_month.append((m, len(cur & set(prev)) / len(cur) * 100))
rr = pd.DataFrame(repeat_rate_by_month, columns=["ym", "rate"])
metrics["avg_monthly_repeat_rate"] = round(float(rr["rate"].mean()), 1)

fig, ax = plt.subplots(figsize=(9, 3.6))
ax.bar(rr["ym"], rr["rate"], color=C["main"], alpha=0.85)
for i, v in enumerate(rr["rate"]):
    ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=8)
ax.set_ylabel("当月买家中的老客占比 %")
ax.set_title("月度复购结构：老客占比平均约 " + f"{metrics['avg_monthly_repeat_rate']}%")
ax.tick_params(axis="x", rotation=45)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "05_repeat.png", bbox_inches="tight")
plt.close(fig)

# ========== 6. 退货分析 ==========
ret_cust = returns[returns["CustomerID"].notna()]
ret_rate = ret_cust["Revenue"].abs().sum() / (ret_cust["Revenue"].abs().sum() + known["Revenue"].sum()) * 100
metrics["return_gmv_rate"] = round(float(ret_rate), 2)
top_ret = ret_cust.groupby("Description")["Quantity"].apply(lambda s: -s[s < 0].sum() if (s < 0).any() else 0).sort_values(ascending=False).head(8)
top_ret = top_ret[top_ret > 0]

# ========== 7. Top 商品与地域 ==========
top_prod = known.groupby("Description")["Revenue"].sum().sort_values(ascending=False).head(8)
metrics["top_products"] = [{"name": k, "gmv": round(float(v), 0)} for k, v in top_prod.items()]
country = known.groupby("Country")["Revenue"].sum().sort_values(ascending=False)
uk_share = float(country.get("United Kingdom", 0) / country.sum() * 100)
metrics["uk_gmv_share"] = round(uk_share, 1)

fig, axes = plt.subplots(1, 2, figsize=(12.5, 4))
tp = top_prod[::-1]
axes[0].barh([n[:28] + ("…" if len(n) > 28 else "") for n in tp.index], tp.values / 1e3, color=C["main"])
axes[0].set_xlabel("销售额（千英镑）")
axes[0].set_title("Top 8 畅销商品（按 GMV）")
axes[0].spines[["top", "right"]].set_visible(False)
non_uk = country.drop("United Kingdom").head(8)[::-1]
axes[1].barh(non_uk.index, non_uk.values / 1e3, color=C["warm"])
axes[1].set_xlabel("销售额（千英镑）")
axes[1].set_title(f"Top 8 海外市场（英国占整体 {uk_share:.0f}%）")
axes[1].spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "06_products_countries.png", bbox_inches="tight")
plt.close(fig)

# ========== 7. Cohort 留存矩阵（按首购月份分组） ==========
first_month = known.groupby("CustomerID")["ym"].min().rename("cohort")
cust_ym = known[["CustomerID", "ym"]].drop_duplicates().join(first_month, on="CustomerID")
cust_ym["period"] = (cust_ym["ym"].str[:4].astype(int) - cust_ym["cohort"].str[:4].astype(int)) * 12 \
    + cust_ym["ym"].str[5:7].astype(int) - cust_ym["cohort"].str[5:7].astype(int)
cohort_sizes = cust_ym.groupby("cohort")["CustomerID"].nunique()
# 注意：除以 cohort_sizes 必须按行对齐（div(axis=0)）。直接用 "/" 会按列对齐，
# 把 cohort 名混进列索引，导致整表错乱——这是本次开发踩过并修复的 pandas 坑。
retention = (cust_ym.pivot_table(index="cohort", columns="period", values="CustomerID",
                                 aggfunc="nunique").div(cohort_sizes, axis=0) * 100)
retention.columns = retention.columns.astype(int)
retention = retention.drop(columns=0)  # 第0月恒为100%
avg_m1 = float(retention[1].dropna().mean()) if 1 in retention.columns else float("nan")
cols3 = [c for c in [1, 2, 3] if c in retention.columns]
metrics["cohort"] = {
    "avg_m1_retention": round(avg_m1, 1),
    "n_cohorts": int(len(cohort_sizes)),
    "note": "留存=该 cohort 客户在第 N 月仍有购买的比例；12月数据不完整已随自然截断展示",
}

fig, ax = plt.subplots(figsize=(10, 4.6))
im = ax.imshow(retention.values, cmap="Greens", aspect="auto", vmin=0, vmax=60)
ax.set_xticks(range(retention.shape[1]), [f"第{c}月" for c in retention.columns], fontsize=9)
ax.set_yticks(range(retention.shape[0]), retention.index, fontsize=9)
for i in range(retention.shape[0]):
    for j in range(retention.shape[1]):
        v = retention.values[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8,
                    color="white" if v > 35 else "#1C2B26")
ax.set_title("Cohort 月度留存矩阵（%，行=首购月份）：首月留存约 "
             f"{avg_m1:.0f}%，B2B 客户粘性极强")
fig.colorbar(im, ax=ax, shrink=0.8, label="留存率 %")
fig.tight_layout()
fig.savefig(OUT / "07_cohort.png", bbox_inches="tight")
plt.close(fig)

# ========== 8. 购物篮分析：商品关联（lift） ==========
basket = known.groupby(["InvoiceNoStr", "Description"])["Quantity"].sum().reset_index()
item_freq = basket["Description"].value_counts()
MIN_FREQ = 50
while True:  # 高频商品过多时自动收紧阈值，控制两两组合规模
    popular = item_freq[item_freq >= MIN_FREQ].index
    if len(popular) <= 400 or MIN_FREQ >= 300:
        break
    MIN_FREQ += 25
b = basket[basket["Description"].isin(popular)]
n_invoices = b["InvoiceNoStr"].nunique()
from collections import Counter
inv_by_item = b.groupby("Description")["InvoiceNoStr"].apply(set).to_dict()
pairs = Counter()
items = list(inv_by_item.keys())
# 组合数较大，仅在高频商品内两两组合
if len(items) <= 400:
    import itertools
    for a, bb in itertools.combinations(sorted(items), 2):
        co = len(inv_by_item[a] & inv_by_item[bb])
        if co >= 15:
            lift = (co / n_invoices) / ((len(inv_by_item[a]) / n_invoices) * (len(inv_by_item[bb]) / n_invoices))
            pairs[(a, bb)] = (co, lift)
top_pairs = sorted(pairs.items(), key=lambda kv: (-kv[1][1]))[:10]
metrics["basket"] = {
    "n_popular_items": int(len(popular)),
    "min_freq": int(MIN_FREQ),
    "min_co_occurrence": 15,
    "top_pairs": [{"a": k[0], "b": k[1], "co": v[0], "lift": round(v[1], 1)}
                  for k, v in top_pairs[:6]],
}

fig, ax = plt.subplots(figsize=(9.5, 4.2))
labels = [f"{k[0][:22]}… + {k[1][:22]}…" if len(k[0]) > 22 or len(k[1]) > 22
          else f"{k[0]} + {k[1]}" for k, _ in top_pairs[:8][::-1]]
lifts = [v[1] for _, v in top_pairs[:8][::-1]]
ax.barh(labels, lifts, color=C["warm"])
for i, (v, (_, (co, _))) in enumerate(zip(lifts, top_pairs[:8][::-1])):
    ax.text(v + 0.05, i, f"{v:.1f}x (n={co})", va="center", fontsize=8)
ax.set_xlabel("提升度 lift（>1 表示正关联）")
ax.set_title("购物篮分析：关联最强的商品组合（共现≥15张发票）")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "08_basket.png", bbox_inches="tight")
plt.close(fig)

# ========== 9. 保存 ==========
(OUT / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: metrics[k] for k in
                  ["rows_total", "n_customers", "gmv_total", "aov", "avg_monthly_repeat_rate",
                   "return_rate_rows", "uk_gmv_share", "peak_month"]},
                 ensure_ascii=False, indent=2))
print("\nRFM 分层：")
print(seg_stat.to_string())
print("\nK-Means：")
print(cl.to_string())
print("\n图表与 metrics.json 已输出到", OUT)
