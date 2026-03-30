#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键运行脚本：自动串联回测 + 报告生成 + 浏览器预览。

用法（无需任何参数，直接运行）:
  python scripts/run_backtest.py

高级用法（自定义参数）:
  python scripts/run_backtest.py \\
    --data_path D:/my_data/510300_data.json \\
    --output_dir D:/output \\
    --monthly_amount 2000 \\
    --take_profit 0.3 \\
    --stop_loss 0.15 \\
    --ts_code 510300.SH \\
    --port 8899

参数说明:
  --data_path      行情数据JSON路径（如不提供，脚本会尝试从工作区自动检测）
  --output_dir     输出目录，默认当前目录
  --monthly_amount 每期基础定投金额（元），默认 1000
  --ma_period      均线周期，默认 30
  --take_profit    止盈阈值（浮盈比例），默认 0.30（即 +30% 止盈）；设为 0 禁用
  --stop_loss      止损阈值（浮亏比例），默认 0.15（即 -15% 止损）；设为 0 禁用
  --ts_code        标的代码（报告展示用），默认 510300.SH
  --port           本地预览服务端口，默认 8899
  --no_browser     加此参数则不自动打开浏览器
"""

import argparse
import os
import sys
import json
import subprocess
import threading
import http.server
import webbrowser
import time

# ── 脚本所在目录（scripts/）
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
# ── 项目根目录（scripts/ 的父目录）
ROOT_DIR    = os.path.dirname(SCRIPTS_DIR)


def parse_args():
    parser = argparse.ArgumentParser(description="MA30趋势过滤器定投策略 — 一键回测运行器")
    parser.add_argument("--data_path",       default=None,         help="行情数据JSON路径（自动检测）")
    parser.add_argument("--output_dir",      default=None,         help="输出目录，默认当前目录或工作区根")
    parser.add_argument("--monthly_amount",  type=float, default=1000.0, help="每期基础定投金额（元）")
    parser.add_argument("--ma_period",       type=int,   default=30,    help="均线周期（交易日数）")
    parser.add_argument("--take_profit",     type=float, default=0.30,  help="止盈阈值，0=禁用，默认0.30")
    parser.add_argument("--stop_loss",       type=float, default=0.15,  help="止损阈值，0=禁用，默认0.15")
    parser.add_argument("--ts_code",         default="510300.SH",   help="标的代码（用于报告标题）")
    parser.add_argument("--port",            type=int,   default=8899,  help="本地预览HTTP服务端口")
    parser.add_argument("--no_browser",      action="store_true",   help="不自动打开浏览器")
    return parser.parse_args()


def find_data_file(ts_code: str, output_dir: str) -> str | None:
    """在常见位置自动查找行情数据 JSON。"""
    candidates = [
        os.path.join(output_dir, f"{ts_code.replace('.', '_')}_data.json"),
        os.path.join(output_dir, f"{ts_code}_data.json"),
        os.path.join(output_dir, "510300_data.json"),
        os.path.join(ROOT_DIR,   f"{ts_code.replace('.', '_')}_data.json"),
        os.path.join(ROOT_DIR,   "510300_data.json"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def run_step(label: str, cmd: list) -> int:
    """执行子进程，实时打印输出，返回退出码。"""
    print(f"\n{'='*60}")
    print(f"[{label}] 开始执行")
    print(f"  命令: {' '.join(cmd)}")
    print('='*60)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace")
    for line in proc.stdout:
        print("  " + line, end="")
    proc.wait()
    if proc.returncode == 0:
        print(f"[{label}] ✅ 完成\n")
    else:
        print(f"[{label}] ❌ 失败（退出码 {proc.returncode}）\n")
    return proc.returncode


def start_preview_server(directory: str, port: int):
    """在后台线程启动简单 HTTP 服务器。"""
    os.chdir(directory)
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *args: None   # 静默日志
    server  = http.server.HTTPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


def main():
    args = parse_args()
    python = sys.executable

    # ── 输出目录
    output_dir = args.output_dir or os.getcwd()
    os.makedirs(output_dir, exist_ok=True)

    # ── 查找数据文件
    data_path = args.data_path
    if not data_path:
        data_path = find_data_file(args.ts_code, output_dir)
    if not data_path or not os.path.isfile(data_path):
        print(f"❌ 找不到行情数据文件，请先获取数据并通过 --data_path 指定路径。")
        print(f"   示例: python scripts/run_backtest.py --data_path D:/510300_data.json")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  MA30 趋势过滤器定投策略 — 一键回测")
    print(f"  数据: {data_path}")
    print(f"  输出目录: {output_dir}")
    print(f"  每期金额: ¥{args.monthly_amount:,.0f}  均线周期: MA{args.ma_period}")
    tp_info = f"+{args.take_profit*100:.0f}%" if args.take_profit > 0 else "禁用"
    sl_info = f"-{args.stop_loss*100:.0f}%" if args.stop_loss > 0 else "禁用"
    print(f"  止盈阈值: {tp_info}  止损阈值: {sl_info}")
    print(f"{'='*60}\n")

    # ─────────────────────────────────────────────
    # Step 1: 回测
    # ─────────────────────────────────────────────
    backtest_script = os.path.join(SCRIPTS_DIR, "backtest.py")
    results_path = os.path.join(output_dir, "backtest_results.json")
    price_path   = os.path.join(output_dir, f"price_ma{args.ma_period}.json")

    rc = run_step("回测引擎", [
        python, backtest_script,
        "--data_path",      data_path,
        "--output_dir",     output_dir,
        "--monthly_amount", str(args.monthly_amount),
        "--ma_period",      str(args.ma_period),
        "--take_profit",    str(args.take_profit),
        "--stop_loss",      str(args.stop_loss),
    ])
    if rc != 0:
        print("❌ 回测失败，中止流程。")
        sys.exit(rc)

    # ─────────────────────────────────────────────
    # Step 2: 生成 HTML 报告
    # ─────────────────────────────────────────────
    report_path  = os.path.join(output_dir, "ma30_dca_report.html")
    report_script = os.path.join(SCRIPTS_DIR, "generate_report.py")

    rc = run_step("报告生成", [
        python, report_script,
        "--results_path",   results_path,
        "--price_path",     price_path,
        "--output_path",    report_path,
        "--ma_period",      str(args.ma_period),
        "--ts_code",        args.ts_code,
        "--monthly_amount", str(args.monthly_amount),
    ])
    if rc != 0:
        print("❌ 报告生成失败，中止流程。")
        sys.exit(rc)

    # ─────────────────────────────────────────────
    # Step 3: 打印摘要
    # ─────────────────────────────────────────────
    try:
        with open(results_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        print(f"\n{'='*60}")
        print(f"  📊 回测摘要")
        print(f"{'='*60}")
        best = max(results, key=lambda x: x["total_return"])
        for r in results:
            tp_cnt = r.get("take_profit_count", 0)
            sl_cnt = r.get("stop_loss_count", 0)
            tp_sl_str = f"  止盈{tp_cnt}次 止损{sl_cnt}次" if (tp_cnt + sl_cnt) > 0 else ""
            mark = " 🏆" if r["name"] == best["name"] else ""
            print(f"  {r['name']}{mark}")
            print(f"    总投入: ¥{r['total_invested']:>10,.2f}  最终市值: ¥{r['final_value']:>10,.2f}")
            sign = "+" if r["total_return"] >= 0 else ""
            print(f"    总收益: {sign}{r['total_return']}%  年化: {sign}{r['annual_return']}%  最大回撤: -{r['max_drawdown']}%{tp_sl_str}")
            print()
    except Exception as e:
        print(f"[摘要] 无法读取回测结果: {e}")

    # ─────────────────────────────────────────────
    # Step 4: 启动本地预览服务器并打开浏览器
    # ─────────────────────────────────────────────
    if not args.no_browser:
        port = args.port
        try:
            start_preview_server(output_dir, port)
            url = f"http://127.0.0.1:{port}/ma30_dca_report.html"
            print(f"{'='*60}")
            print(f"  🌐 本地预览服务已启动: {url}")
            print(f"  按 Ctrl+C 停止")
            print(f"{'='*60}\n")
            time.sleep(0.5)
            webbrowser.open(url)
            # 保持主线程存活，让 HTTP 服务器继续跑
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[预览服务] 已停止。")
    else:
        print(f"\n✅ 全部完成！")
        print(f"   报告路径: {report_path}")
        print(f"   用浏览器直接打开该文件即可查看。\n")


if __name__ == "__main__":
    main()
