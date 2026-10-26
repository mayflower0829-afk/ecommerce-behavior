# 电商用户行为分析 · E-commerce Behavior Analytics

基于 UCI「Online Retail」真实交易数据集（英国线上批发商，2010-12 ~ 2011-12，54 万行）的**用户行为完整分析**：KPI 总览 → 时段规律 → RFM 分层 → K-Means 聚类 → 复购留存 → 退货分析。

**在线报告**：<https://cloud1-d4gsgj705497df85d-1501559031.tcloudbaseapp.com/ecommerce/>

## 核心发现

| 发现 | 数字 | 运营含义 |
|---|---|---|
| 二八效应显著 | 26% 的「重要价值客户」贡献 **66.5%** GMV | 资源向留存与召回两端集中 |
| B2B 强复购结构 | 月均 **70.6%** 当月买家为老客 | 营销预算偏向留存而非拉新 |
| 下单集中办公时间 | 工作日上午 10-12 点为峰值；周六不营业 | 排班、推送时机据此对齐 |
| 旺季明确 | 9-11 月走旺，峰值 2011-11 | 备货与物流提前规划 |

K-Means（对 R、logF、logM 标准化聚类，肘部法则选 k=4）独立分离出「高频高额核心客群（人均 £10,007）」与「流失客群（平均 259 天未购）」，与 RFM 规则分层相互印证。

## 方法要点

- **清洗口径**：退货/取消单（负数量、C 开头发票）单独分析；单价 ≤0 的调整行剔除；CustomerID 缺失 24.9% 订单不参与客户级分析——口径清晰可解释。
- **RFM 双重验证**：五分位打分的业务分层 + 无监督聚类交叉印证，说明分层结论不是打分规则的人为产物。
- **诚实声明**：B2B 场景结论不可直接外推 C 端；无浏览/购物车事件故不做漏斗；2011-12 仅 9 天数据已标注截断。

## 目录结构

```
ecommerce-behavior/
├── data/                # UCI 原始数据（xlsx）
├── src/
│   ├── analysis.py      # 完整分析流水线（输出图表 PNG + metrics.json）
│   └── build_report.py  # 由 metrics+图表生成在线 HTML 报告
└── public/              # 部署产物（在线报告页）
```

## 复现

```bash
pip install pandas numpy scikit-learn matplotlib openpyxl
python3 src/analysis.py       # 跑完整流水线，输出 output/
python3 src/build_report.py   # 生成 public/index.html 报告页
```

数据来源：[UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail)（Chen, Sain & Guo, 2012）。

## License

MIT
