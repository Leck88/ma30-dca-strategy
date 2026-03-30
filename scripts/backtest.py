#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
30均线趋势过滤器 + 定投联合策略 — 回测引擎（含止盈止损）

用法:
  python backtest.py --data_path <JSON> [--output_dir <目录>]
                     [--monthly_amount 1000] [--ma_period 30]
                     [--take_profit 0.3] [--stop_loss 0.15]

止盈止损说明:
  --take_profit  浮盈比例阈值（相对于总投入），如 0.3 = 盈利30%时止盈
  --stop_loss    浮亏比例阈值（绝对值），如 0.15 = 亏损15%时止损
  设为 0 则禁用对应规则，默认 take_profit=0.3, stop_loss=0.15
"""

import json
import os
import argparse
from datetime import datetime


# ===================================================
# 命令行参数
# ===================================================
def parse_args():
    parser = argparse.ArgumentParser(description="30均线趋势过滤器定投策略回测")
    parser.add_argument("--data_path",       required=True,            help="行情数据JSON文件路径")
    parser.add_argument("--output_dir",      default=".",              help="结果输出目录，默认当前目录")
    parser.add_argument("--monthly_amount",  type=float, default=1000.0, help="每期基础定投金额（元）")
    parser.add_argument("--ma_period",       type=int,   default=30,   help="均线周期（交易日数）")
    parser.add_argument("--take_profit",     type=float, default=0.30, help="止盈阈值（浮盈比例），0 禁用，默认0.3")
    parser.add_argument("--stop_loss",       type=float, default=0.15, help="止损阈值（浮亏比例），0 禁用，默认0.15")
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
# 回测引擎（含止盈止损）
# ===================================================
def backtest(name: str, dates: list, closes: list, ma: list,
             invest_indices: list, invest_amount_func,
             take_profit: float = 0.30, stop_loss: float = 0.15) -> dict:
    """
    通用回测引擎，支持止盈止损。

    止盈止损逻辑（每个交易日收盘后检测）：
      - 止盈: 当日市值 >= 总投入 * (1 + take_profit) → 全部卖出，重置持仓
      - 止损: 当日市值 <= 总投入 * (1 - stop_loss)  → 全部卖出，重置持仓
      触发后，下一个定投日恢复正常定投节奏。

    invest_amount_func(idx, ma_val, price, total_shares) -> float
      返回本次投入金额，0 表示暂停。
    """
    total_invested = 0.0
    total_shares   = 0.0
    realized_pnl   = 0.0   # 历次止盈止损累计变现损益
    records_log    = []
    tp_sl_log      = []    # 止盈止损事件记录
    nav_series     = []    # list of (date_str, portfolio_value, total_invested)

    # 第一次买入前，净值序列填 0
    for i in range(invest_indices[0]):
        nav_series.append((str(dates[i]), 0.0, 0.0))

    # 逐日遍历（以定投日为驱动，但每日检测止盈止损）
    invest_idx_iter = iter(enumerate(invest_indices))
    next_invest_enum = next(invest_idx_iter, None)

    for day_i, (d, price) in enumerate(zip(dates, closes)):
        # ——— 定投日：执行买入 ———
        if next_invest_enum is not None:
            order_seq, invest_i = next_invest_enum
            if day_i == invest_i:
                ma_val = ma[day_i]
                amount = invest_amount_func(day_i, ma_val, price, total_shares)

                if amount > 0:
                    shares_bought   = amount / price
                    total_shares   += shares_bought
                    total_invested += amount
                    action = f"买入 {shares_bought:.4f}份 @{price:.3f}"
                else:
                    action = "暂停定投"

                records_log.append({
                    "date":            str(d),
                    "price":           round(price, 3),
                    "ma30":            round(ma_val, 3) if ma_val else None,
                    "amount":          round(amount, 2),
                    "action":          action,
                    "total_invested":  round(total_invested, 2),
                    "total_shares":    round(total_shares, 4),
                    "portfolio_value": round(total_shares * price, 2),
                    "type":            "invest",
                })
                next_invest_enum = next(invest_idx_iter, None)

        # ——— 每日收盘后：检测止盈止损 ———
        if total_shares > 0 and total_invested > 0:
            portfolio_val = total_shares * price

            # 止盈检测
            if take_profit > 0 and portfolio_val >= total_invested * (1 + take_profit):
                profit    = portfolio_val - total_invested
                gain_pct  = profit / total_invested * 100
                realized_pnl += profit
                tp_sl_log.append({
                    "date":            str(d),
                    "price":           round(price, 3),
                    "type":            "take_profit",
                    "label":           f"止盈 +{gain_pct:.1f}%",
                    "portfolio_value": round(portfolio_val, 2),
                    "total_invested":  round(total_invested, 2),
                    "profit":          round(profit, 2),
                    "gain_pct":        round(gain_pct, 2),
                })
                records_log.append({
                    "date":            str(d),
                    "price":           round(price, 3),
                    "ma30":            round(ma[day_i], 3) if ma[day_i] else None,
                    "amount":          -round(portfolio_val, 2),
                    "action":          f"🎯 止盈卖出 全部{total_shares:.4f}份 @{price:.3f}，盈利 ¥{profit:.2f}（+{gain_pct:.1f}%）",
                    "total_invested":  0.0,
                    "total_shares":    0.0,
                    "portfolio_value": 0.0,
                    "type":            "take_profit",
                })
                # 清仓，重新开始
                total_shares   = 0.0
                total_invested = 0.0

            # 止损检测
            elif stop_loss > 0 and portfolio_val <= total_invested * (1 - stop_loss):
                loss      = total_invested - portfolio_val
                loss_pct  = loss / total_invested * 100
                realized_pnl -= loss
                tp_sl_log.append({
                    "date":            str(d),
                    "price":           round(price, 3),
                    "type":            "stop_loss",
                    "label":           f"止损 -{loss_pct:.1f}%",
                    "portfolio_value": round(portfolio_val, 2),
                    "total_invested":  round(total_invested, 2),
                    "profit":          -round(loss, 2),
                    "gain_pct":        -round(loss_pct, 2),
                })
                records_log.append({
                    "date":            str(d),
                    "price":           round(price, 3),
                    "ma30":            round(ma[day_i], 3) if ma[day_i] else None,
                    "amount":          -round(portfolio_val, 2),
                    "action":          f"🛑 止损卖出 全部{total_shares:.4f}份 @{price:.3f}，亏损 ¥{loss:.2f}（-{loss_pct:.1f}%）",
                    "total_invested":  0.0,
                    "total_shares":    0.0,
                    "portfolio_value": 0.0,
                    "type":            "stop_loss",
                })
                # 清仓，重新开始
                total_shares   = 0.0
                total_invested = 0.0

        # ——— 记录每日净值（含变现损益）———
        current_val = total_shares * price + realized_pnl
        nav_series.append((str(d), round(current_val, 2), round(total_invested, 2)))

    # ——— 期末结算 ———
    final_market_val = total_shares * closes[-1]
    final_value      = final_market_val + realized_pnl

    # 计算累计总投入（所有未卖出 + 已清仓的历史投入之和，用于评估总回报）
    # 从 records_log 重算：所有 invest 类型的买入金额之和
    cum_invested = sum(r["amount"] for r in records_log if r.get("type") == "invest" and r["amount"] > 0)

    total_return = (final_value / cum_invested - 1) * 100 if cum_invested > 0 else 0

    n_years = (dates[-1] - dates[invest_indices[0]]).days / 365.0
    annual_return = ((final_value / cum_invested) ** (1.0 / n_years) - 1) * 100 \
                    if cum_invested > 0 and n_years > 0 else 0

    # 最大回撤（基于每日组合市值，含已变现）
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
        "name":            name,
        "total_invested":  round(cum_invested, 2),
        "final_value":     round(final_value, 2),
        "realized_pnl":    round(realized_pnl, 2),
        "total_return":    round(total_return, 2),
        "annual_return":   round(annual_return, 2),
        "max_drawdown":    round(max_dd * 100, 2),
        "nav_series":      nav_series,
        "trade_log":       records_log,
        "tp_sl_log":       tp_sl_log,
        "invest_count":    sum(1 for r in records_log if r.get("type") == "invest" and r["amount"] > 0),
        "skip_count":      sum(1 for r in records_log if r.get("type") == "invest" and r["amount"] == 0),
        "take_profit_count": sum(1 for e in tp_sl_log if e["type"] == "take_profit"),
        "stop_loss_count":   sum(1 for e in tp_sl_log if e["type"] == "stop_loss"),
        "config": {
            "take_profit": take_profit,
            "stop_loss":   stop_loss,
        },
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
        ("普通定投",      plain_dca),
        ("趋势加倍定投",  trend_double_dca),
        ("趋势暂停定投",  trend_stop_dca),
        ("趋势分级定投",  trend_tiered_dca),
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

    # 止盈止损参数
    tp = args.take_profit
    sl = args.stop_loss
    if tp > 0:
        print(f"[backtest] 止盈阈值: +{tp*100:.0f}%  止损阈值: -{sl*100:.0f}%")
    else:
        print("[backtest] 止盈止损: 已禁用")

    # 执行回测
    strategies = build_strategies(args.monthly_amount)
    results = []
    for name, func in strategies:
        r = backtest(name, dates, closes, ma, invest_indices, func,
                     take_profit=tp, stop_loss=sl)
        results.append(r)
        tp_info = f"  止盈{r['take_profit_count']}次 止损{r['stop_loss_count']}次" if tp > 0 else ""
        print(f"  [{name}] 总收益率: {r['total_return']}%  年化: {r['annual_return']}%  "
              f"最大回撤: {r['max_drawdown']}%{tp_info}")

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
