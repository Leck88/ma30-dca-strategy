#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
30均线趋势过滤器 + 定投联合策略 — 回测引擎
用法:
  python backtest.py --data_path <JSON> [--output_dir <目录>] [--monthly_amount 1000] [--ma_period 30]
"""

import json
import os
import math
import argparse
from datetime import datetime, date


# ===================================================
# 命令行参数
# ===================================================
def parse_args():
    parser = argparse.ArgumentParser(description="30均线趋势过滤器定投策略回测")
    parser.add_argument("--data_path",      required=True, help="行情数据JSON文件路径（finance-data-retrieval 输出）")
    parser.add_argument("--output_dir",     default=".",   help="结果输出目录，默认当前目录")
    parser.add_argument("--monthly_amount", type=float, default=1000.0, help="每期基础定投金额（元），默认1000")
    parser.add_argument("--ma_period",      type=int,   default=30,    help="均线周期（交易日数），默认30")
    return parser.parse_args()


# ===================================================
# 数据加载
# ===================================================
def load_data(data_path: str):
    """
    加载 finance-data-retrieval 返回的 JSON（fund_daily / daily 格式）。
    返回按日期升序排列的 records 列表，每项包含: date, open, high, low, close, vol
    """
    with open(data_path, "r", encoding="utf-8-sig") as f:
        raw = json.load(f)

    fields = raw["data"]["fields"]
    items  = raw["data"]["items"]

    records = []
    for row in items:
        d = dict(zip(fields, row))
        records.append({
            "date":  datetime.strptime(d["trade_date"], "%Y%m%d").date(),
            "open":  float(d["open"]),
            "close": float(d["close"]),
            "high":  float(d["high"]),
            "low":   float(d["low"]),
            "vol":   float(d["vol"]),
        })

    records.sort(key=lambda x: x["date"])
    return records


# ===================================================
# 计算移动均线
# ===================================================
def calc_ma(closes: list, period: int) -> list:
    """计算简单移动平均线，前 period-1 个点返回 None。"""
    ma = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        ma[i] = sum(closes[i - period + 1 : i + 1]) / period
    return ma


# ===================================================
# 确定每月第一个交易日索引
# ===================================================
def get_monthly_invest_indices(dates: list) -> list:
    monthly_first = {}
    for i, d in enumerate(dates):
        key = (d.year, d.month)
        if key not in monthly_first:
            monthly_first[key] = i
    return sorted(monthly_first.values())


# ===================================================
# 回测引擎
# ===================================================
def backtest(name: str, dates: list, closes: list, ma: list,
             invest_indices: list, invest_amount_func) -> dict:
    """
    通用回测引擎。
    invest_amount_func(idx, ma_val, price, total_shares) -> float
      返回本次投入金额，0 表示暂停。
    """
    total_invested = 0.0
    total_shares   = 0.0
    records_log    = []
    nav_series     = []   # list of (date_str, portfolio_value, total_invested)

    # 第一次买入前，净值序列填0
    for i in range(invest_indices[0]):
        nav_series.append((str(dates[i]), 0.0, 0.0))

    for idx, i in enumerate(invest_indices):
        price  = closes[i]
        ma_val = ma[i]
        amount = invest_amount_func(i, ma_val, price, total_shares)

        if amount > 0:
            shares_bought = amount / price
            total_shares += shares_bought
            total_invested += amount
            action = f"买入 {shares_bought:.4f}份 @{price:.3f}"
        else:
            action = "暂停定投"

        records_log.append({
            "date":            str(dates[i]),
            "price":           round(price, 3),
            "ma30":            round(ma_val, 3) if ma_val else None,
            "amount":          amount,
            "action":          action,
            "total_invested":  round(total_invested, 2),
            "total_shares":    round(total_shares, 4),
            "portfolio_value": round(total_shares * price, 2),
        })

        # 当前定投日 → 下一次定投日（或末尾）的每日净值
        next_i = invest_indices[idx + 1] if idx + 1 < len(invest_indices) else len(dates)
        for j in range(i, next_i):
            portfolio_val = total_shares * closes[j]
            nav_series.append((str(dates[j]), portfolio_val, total_invested))

    # ——— 汇总统计 ———
    final_value  = total_shares * closes[-1]
    total_return = (final_value - total_invested) / total_invested * 100 if total_invested > 0 else 0

    n_years      = (dates[-1] - dates[invest_indices[0]]).days / 365.0
    annual_return = ((final_value / total_invested) ** (1.0 / n_years) - 1) * 100 \
                    if total_invested > 0 and n_years > 0 else 0

    # 最大回撤（基于每日组合市值）
    max_dd   = 0.0
    peak_val = 0.0
    for _, val, _ in nav_series:
        if val > peak_val:
            peak_val = val
        if peak_val > 0:
            dd = (peak_val - val) / peak_val
            if dd > max_dd:
                max_dd = dd

    return {
        "name":          name,
        "total_invested": round(total_invested, 2),
        "final_value":    round(final_value, 2),
        "total_return":   round(total_return, 2),
        "annual_return":  round(annual_return, 2),
        "max_drawdown":   round(max_dd * 100, 2),
        "nav_series":     nav_series,
        "trade_log":      records_log,
        "invest_count":   sum(1 for r in records_log if r["amount"] > 0),
        "skip_count":     sum(1 for r in records_log if r["amount"] == 0),
    }


# ===================================================
# 四种策略定义
# ===================================================
def build_strategies(monthly_amount: float):
    """返回四种策略的 (名称, 函数) 元组列表。"""

    def plain_dca(i, ma_val, price, shares):
        """策略1: 普通定投 — 每月固定金额，忽略趋势"""
        return monthly_amount

    def trend_double_dca(i, ma_val, price, shares):
        """策略2: 趋势加倍定投 — 低于MA加倍买入"""
        if ma_val is None:
            return monthly_amount
        return monthly_amount * 2 if price <= ma_val else monthly_amount

    def trend_stop_dca(i, ma_val, price, shares):
        """策略3: 趋势暂停定投 — 低于MA暂停投入"""
        if ma_val is None:
            return monthly_amount
        return 0 if price <= ma_val else monthly_amount

    def trend_tiered_dca(i, ma_val, price, shares):
        """策略4: 趋势分级定投 — 按偏离程度动态调整倍数"""
        if ma_val is None:
            return monthly_amount
        ratio = (price - ma_val) / ma_val  # 正=在均线上，负=在均线下
        if   ratio >=  0.05: return monthly_amount * 0.5
        elif ratio >=  0.00: return monthly_amount * 1.0
        elif ratio >= -0.05: return monthly_amount * 1.5
        elif ratio >= -0.10: return monthly_amount * 2.0
        else:                return monthly_amount * 3.0

    return [
        ("普通定投",          plain_dca),
        ("趋势加倍定投",      trend_double_dca),
        ("趋势暂停定投",      trend_stop_dca),
        ("趋势分级定投",      trend_tiered_dca),
    ]


# ===================================================
# 主函数
# ===================================================
def main():
    args = parse_args()

    print(f"[backtest] 加载数据: {args.data_path}")
    records = load_data(args.data_path)
    dates  = [r["date"]  for r in records]
    closes = [r["close"] for r in records]

    print(f"[backtest] 数据区间: {dates[0]} ~ {dates[-1]}，共 {len(dates)} 个交易日")

    # 计算均线
    ma = calc_ma(closes, args.ma_period)
    print(f"[backtest] 计算 MA{args.ma_period} 完成")

    # 月度定投日
    invest_indices = get_monthly_invest_indices(dates)
    print(f"[backtest] 共 {len(invest_indices)} 个定投日")

    # 执行回测
    strategies = build_strategies(args.monthly_amount)
    results = []
    for name, func in strategies:
        r = backtest(name, dates, closes, ma, invest_indices, func)
        results.append(r)
        print(f"  [{name}] 总收益率: {r['total_return']}%  年化: {r['annual_return']}%  最大回撤: {r['max_drawdown']}%")

    # 保存 backtest_results.json
    os.makedirs(args.output_dir, exist_ok=True)
    results_path = os.path.join(args.output_dir, "backtest_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[backtest] 回测结果已保存: {results_path}")

    # 保存 price_ma<N>.json（供报告使用）
    price_data = [(str(d), c, m) for d, c, m in zip(dates, closes, ma)]
    price_path = os.path.join(args.output_dir, f"price_ma{args.ma_period}.json")
    with open(price_path, "w", encoding="utf-8") as f:
        json.dump(price_data, f, ensure_ascii=False)
    print(f"[backtest] 价格+均线数据已保存: {price_path}")

    return results_path, price_path


if __name__ == "__main__":
    main()
