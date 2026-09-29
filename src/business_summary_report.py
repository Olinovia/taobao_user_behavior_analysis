"""
data_dashboard.py
--------------------------------
功能: 生成 Markdown 分析总览展示看板，汇总各分析函数结果并写入 .md 文件。
数据分析模块，包含：
    - pct
    - fmt_num
    - df_to_md
    - build_weekly_report
    - write_weekly_report
输出内容：
    - md数据分析总览展示看板  business_summary_report.md

依赖：pandas、numpy
"""


from __future__ import annotations

from pathlib import Path
import sys

from datetime import datetime
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(r"C:\Users\Administrator\Desktop\user_behaivor_analysis")
DEFAULT_INPUT = PROJECT_ROOT / "data" / "cleaned_user_behavior.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "dashboard" / "business_summary_report.md"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from data_analysis import (
    load_data,
    summarize_behavior_metrics,
    behavior_type_distribution,
    user_level_funnel,
    user_item_sequential_funnel,
    daily_active_users,
    daily_purchase_trend,
    top_categories_by_purchase,
    repurchase_analysis,
    category_converison_decision_cycle,
    repurchase_cycle,
)

#1.处理字段和值的类型，设置输出md文档的格式。
def pct(x) -> str:
    return f"{float(x):.1%}"


def fmt_num(x) -> str:
    if pd.isna(x):
        return "-"
    return f"{int(x):,}" if float(x).is_integer() else f"{float(x):,.2f}"


def df_to_md(df: pd.DataFrame, columns=None, max_rows=10) -> str:
    if df is None or df.empty:
        return "_暂无数据_"

    x = df.copy()
    if columns:
        x = x[[c for c in columns if c in x.columns]]
    x = x.head(max_rows).copy()

    for col in x.columns:
        if any(k in col for k in ["rate", "pct", "share", "conversion"]):
            x[col] = x[col].map(lambda v: pct(v) if pd.notna(v) else "-")
        elif pd.api.types.is_numeric_dtype(x[col]):
            x[col] = x[col].map(fmt_num)

    return x.to_markdown(index=False)


#2.为生成md数据分析总览看板报告，汇总函数结果和设定报告格式。
def build_business_summary_report(df: pd.DataFrame) -> str:
    core = summarize_behavior_metrics(df)
    dist = behavior_type_distribution(df)
    funnel = user_level_funnel(df)
    seq = user_item_sequential_funnel(df)
    dau = daily_active_users(df)
    purchase = daily_purchase_trend(df)
    categories = top_categories_by_purchase(df, top_n=5)
    repurchase = repurchase_analysis(df)
    decision = category_converison_decision_cycle(df, top_n=10)
    repurchase_cycle_result = repurchase_cycle(df)

    start_date = pd.to_datetime(df["date"]).min().strftime("%Y-%m-%d")
    end_date = pd.to_datetime(df["date"]).max().strftime("%Y-%m-%d")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    peak_dau = dau.loc[dau["dau"].idxmax()]
    latest_dau = int(dau.iloc[-1]["dau"])
    first_dau = int(dau.iloc[0]["dau"])
    dau_change = latest_dau / first_dau - 1 if first_dau else 0

    behavior_share = {
        row["behavior_type"]: row["behavior_share"]
        for _, row in dist.iterrows()
    }

    return f"""# 用户行为经营分析周报

> 数据来源：历史样本,Taobao User Behavior 数据集
> 数据范围：{start_date} ～ {end_date}
> 数据量：约 10 万条用户行为记录
> 分析维度：用户、商品、类目、行为、时间
> 报告生成：{generated_at} 

 本报告基于公开淘宝 `UserBehavior.csv` 数据集抽取的 100,000 行真实样本。清洗后共保留 99,956 条有效行为记录，覆盖 983 名用户。所有涉及日期和小时的指标均按 `Asia/Shanghai` 统计。

---

## 01｜本周经营结论

> ### **流量规模具备基础，但用户行为明显偏浏览，当前最值得优化的是“浏览 → 购买意向”的中段转化；已购买用户具备继续经营空间。**

### 三项重点发现

| 优先级 | 发现 | 数据依据 | 经营含义 |
|---|---|---|---|
| 🔴 P0 | 浏览多，意向行为弱 | PV 占比 **{pct(behavior_share.get("pv", 0))}** | 优先提升详情页、推荐、价格/权益信息 |
| 🔴 P0 | 加购后成交效率更高 | 加购→购买 **{pct(seq["cart_to_buy_pair_rate"])}** | 资源应前移到“浏览→加购/收藏” |
| 🟡 P1 | 已购买用户具备继续经营空间 | 复购用户占购买用户 **{pct(repurchase["repurchase_rate"])}** | 建立二购与老客经营机制 |

### 本期行动重点

**P0｜转化**  
优化 PV → 加购/收藏链路。

**P1｜召回**  
建立加购未购、收藏未购、首购未复购三类人群触达。

**P1｜时间运营**  
把晚间高活跃时段作为转化运营重点窗口。

---

# 02｜经营看板

| 核心指标 | 结果 | 业务含义 |
|---|---:|---|
| **UV** | **{core["uv"]:,}** | 样本用户规模 |
| **行为量** | **{core["total_behavior"]:,}** | 用户行为总量 |
| **峰值 DAU** | **{int(peak_dau["dau"]):,}** | 观测期最高活跃 |
| **购买用户** | **{repurchase["total_buyers"]:,}** | 有购买行为用户 |
| **浏览→购买** | **{pct(core["browse_to_purchase_user_rate"])}** | 用户级组合口径 |
| **加购→购买** | **{pct(core["cart_to_purchase_user_rate"])}** | 用户级组合口径 |
| **复购用户占比** | **{pct(repurchase["repurchase_rate"])}** | 当前事件口径 |

### 行为结构

{df_to_md(dist, ["behavior_type", "behavior_count", "behavior_share"], 10)}

**关键判断**：行为结构越集中于 PV，越需要关注“浏览后的意向形成”。

---

# 03｜活跃与交易趋势

### DAU日活跃度趋势

{df_to_md(dau, ["date", "dau"], 20)}

**趋势**：观测期 DAU 从 **{first_dau:,}** 变为 **{latest_dau:,}**，区间变化 **{dau_change:+.1%}**；峰值为 **{int(peak_dau["dau"]):,}**。


### 观测期交易情况

{df_to_md(purchase, ["date", "purchase_count", "purchase_users"], 20)}

**交易情况**：总体交易量在观测期内持续上升，平均日交易量为**{purchase['purchase_count'].mean():.0f}**，平均日交易人数为**{purchase['purchase_users'].mean():.0f}**。

---

# 04｜转化漏斗

### 用户级漏斗
  
用户级漏斗根据独立用户行为分层，然后计算收藏、加购物车、购买行为分别对浏览行为的转化率漏斗。

{df_to_md(funnel, ["step", "users", "conversation_from_view"], 10)}

### User-Item 顺序漏斗

由用户行为链路推进的用户行为顺序漏斗转化率情况。

| 环节 | 转化率 |
|---|---:|
| PV → 加购 | **{pct(seq["pv_to_cart_pair_rate"])}** |
| PV → 购买 | **{pct(seq["pv_to_buy_pair_rate"])}** |
| 加购 → 购买 | **{pct(seq["cart_to_buy_pair_rate"])}** |
| 收藏 → 购买 | **{pct(seq["fav_to_buy_pair_rate"])}** |

**漏斗定位**：最值得优先优化的是 **PV → 加购/收藏**，因为高意向用户进入加购后，成交效率相对更高。

### 运营方向和指标监测

通过上述不同用户行为漏斗转化的情况，可以设置用户行为运营优化锚点，执行相关主指标监测。

| 优化方向 | 主指标 | 指标监测 |
|---|---| --- |
| 商品详情页优化 | PV→加购 | pv_cart_conversion |
| 价格/优惠强化 | 加购率、购买率 | carted_rate、bought_rate |
| 个性化推荐 | 推荐点击、加购 | top_category、top_item |
| 加购未购召回 | 加购→购买 | cart_buy_conversion |

**优化展望**：拼团、砍一刀等下沉功能。

---

# 05｜用户分层

统计不同用户行为逻辑下的用户分层情况，逐层确定运营目标。

| 人群 | 分层逻辑 | 运营目标 |
|---|---|---|
| **core_user** | 购买≥3 且活跃≥5天 | 复购、客单、会员 |
| **buy_user** | 购买≥1 | 二购 |
| **willing_user** | 收藏≥1 且加购≥1 | 临门转化 |
| **browsing_user** | 其他用户 | 培养购买意向 |

**经营逻辑**：从“统一运营”转向“按行为深度运营”。

---

# 06｜品类经营

### TOP购买品类

{df_to_md(categories, ["category_id", "purchase_count", "buyer_count"], 10)}

### 决策周期

- 有效 PV→购买样本：**{decision["conversion_total"]:,}**
- 平均决策时长：**{decision["avg_decision_length"]:.2f} 分钟**
- 中位决策时长：**{decision["median_decision_length"]:.2f} 分钟**

### 品类策略

**在品类经营部分不只看规模，应同时观察：购买规模 × 浏览转化 × 加购转化。**

---

# 07｜时间运营

### 经营结论

**工作日与周末的行为结构接近，但整体量存在差异；行为在晚间明显集中。**

### 建议

**统一主策略 + 高峰时段加权**

重点投放：

- 加购召回
- 优惠提醒
- 个性化推荐
- 活动入口
- 核心品类资源位

---

# 08｜复购与留存

### 复购

| 指标 | 结果 |
|---|---:|
| 购买用户 | **{repurchase["total_buyers"]:,}** |
| ≥2 次购买用户 | **{repurchase["repurchase_users"]:,}** |
| 当前事件口径复购占比 | **{pct(repurchase["repurchase_rate"])}** |
| 平均事件间隔 | **{repurchase_cycle_result["avg_repurchase_interval"]:.2f} 天** |
| 中位事件间隔 | **{repurchase_cycle_result["median_repurchase_interval"]:.2f} 天** |

**口径风险**：事件间隔可能包含同日多次购买，不应直接解释为标准“用户复购周期”。

### 留存

当前数据窗口较短，正式经营看板建议固定输出：

`D1 / D3 / D7 / D14 / D30`

并采用 cohort 观察不同首日用户的留存。

---

# 09｜经营总结

## 核心判断

```text
流量
 ↓
浏览占主导
 ↓
意向形成不足   ← 当前优先优化
 ↓
高意向用户成交
 ↓
二购 / 复购经营
```

## 当前最值得做的三件事

**P0｜提升浏览→意向**  
优化详情页、推荐和价格/权益表达。

**P0｜经营高意向未购**  
建立加购未购、收藏未购的触达机制。

**P1｜经营已购买用户**  
建立首购后 1/3/7 天触达和关联品推荐。

---

# 10｜运营行动单

| 优先级 | 事项 | Owner | 验证指标 | 执行方式 |
|---|---|---|---|---|
| P0 | PV→加购优化 | 产品/运营 | PV→加购率 | A/B Test |
| P0 | 加购未购召回 | 运营 | 加购→购买率 | 分群触达 |
| P1 | 首购后二购 | 运营 | 二购率 | 1/3/7天触达 |
| P1 | 晚间资源倾斜 | 运营 | 时段 CVR | 时段实验 |
| P2 | 品类经营看板 | 产品/数据 | 品类 CVR | 建立矩阵 |
| P2 | 留存 cohort | 数据 | D1/D3/D7 | 补齐口径 |

---

# 11｜数据口径与风险提示

> **以下内容建议固定放在每期周报底部。**

1. 当前数据覆盖 **{start_date} ～ {end_date}**，不是实时业务数据。
2. 用户级漏斗与 user-item 顺序漏斗统计单位不同，不能直接横向比较。
3. 复购按购买事件计算，不等同于订单级复购。
4. 当前缺少 GMV、订单金额、渠道、活动、优惠券、新老客等字段，暂不足以完整解释收入变化。
5. “当前业务建议”是基于历史行为基线给出的运营动作，不应解释为 2026 年市场事实。

---

## Appendix｜指标定义

| 指标 | 定义 |
|---|---|
| UV | 去重用户数 |
| DAU | 单日去重活跃用户 |
| PV | 浏览行为次数 |
| PV→加购 | user-item 顺序口径中，浏览后完成加购的比例 |
| 加购→购买 | user-item 顺序口径中，加购后完成购买的比例 |
| 复购用户 | 购买行为次数 ≥2 的用户 |
| core_user | 购买≥3 且活跃≥5天 |
| willing_user | 同时发生收藏和加购 |
"""


#3.md数据分析总览报告输出路径。
def write_weekly_report(df: pd.DataFrame, output_path=DEFAULT_OUTPUT):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_business_summary_report(df), encoding="utf-8")
    return output_path


#4.总函数。
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate internet-company-style weekly report.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    data = load_data(args.input)
    output = write_weekly_report(data, args.output)
    print(f"Report written to: {output}")
