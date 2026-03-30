#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
30均线趋势过滤器定投策略 — 交互式HTML报告生成器
用法:
  python generate_report.py --results_path <JSON> --price_path <JSON> [--output_path <HTML>] [--ma_period 30]
"""

import json
import argparse
import os


def parse_args():
    parser = argparse.ArgumentParser(description="生成定投策略回测HTML报告")
    parser.add_argument("--results_path", required=True, help="backtest_results.json 路径")
    parser.add_argument("--price_path",   required=True, help="price_ma<N>.json 路径")
    parser.add_argument("--output_path",  default=None,  help="输出HTML文件路径（默认与results同目录）")
    parser.add_argument("--ma_period",    type=int, default=30, help="均线周期，用于图表标题展示，默认30")
    parser.add_argument("--ts_code",      default="510300.SH", help="标的代码，用于报告标题")
    parser.add_argument("--start_date",   default="", help="回测起始日期（展示用）")
    parser.add_argument("--end_date",     default="", help="回测结束日期（展示用）")
    parser.add_argument("--monthly_amount", type=float, default=1000.0, help="基础定投金额")
    return parser.parse_args()


def generate_html(results: list, price_ma30: list, ma_period: int,
                  ts_code: str, start_date: str, end_date: str, monthly_amount: float) -> str:
    results_json = json.dumps(results, ensure_ascii=False)
    price_json   = json.dumps(price_ma30, ensure_ascii=False)

    date_range = f"{start_date} ~ {end_date}" if start_date and end_date else "历史区间"
    ma_label   = f"MA{ma_period}"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{ma_label}趋势过滤器 · 定投策略回测报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: #0d1117;
    color: #e6edf3;
    min-height: 100vh;
  }}

  /* ===== 顶栏 ===== */
  .header {{
    background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%);
    border-bottom: 1px solid #21262d;
    padding: 28px 40px 24px;
    position: relative;
    overflow: hidden;
  }}
  .header::before {{
    content: '';
    position: absolute; top: -50%; left: -10%;
    width: 120%; height: 200%;
    background: radial-gradient(ellipse at 30% 50%, rgba(88,166,255,0.06) 0%, transparent 60%);
    pointer-events: none;
  }}
  .header-inner {{ max-width: 1400px; margin: 0 auto; position: relative; }}
  .badge {{
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(88,166,255,0.12); border: 1px solid rgba(88,166,255,0.3);
    color: #58a6ff; padding: 4px 12px; border-radius: 20px;
    font-size: 12px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 12px;
  }}
  .title {{ font-size: 28px; font-weight: 700; color: #f0f6fc; margin-bottom: 6px; }}
  .subtitle {{ font-size: 14px; color: #8b949e; line-height: 1.5; }}
  .subtitle span {{ color: #58a6ff; font-weight: 500; }}

  /* ===== 主内容 ===== */
  .main {{ max-width: 1400px; margin: 0 auto; padding: 32px 40px; }}

  /* ===== 策略卡片 ===== */
  .strategy-cards {{
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px;
  }}
  .strategy-card {{
    background: #161b22; border: 1px solid #21262d; border-radius: 12px;
    padding: 20px; cursor: pointer; transition: all 0.2s;
    position: relative; overflow: hidden;
  }}
  .strategy-card:hover {{ border-color: #30363d; transform: translateY(-2px); }}
  .strategy-card.active {{ border-color: var(--color); background: rgba(88,166,255,0.04); }}
  .strategy-card::after {{
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 3px; background: var(--color); border-radius: 12px 12px 0 0;
  }}
  .s-icon {{
    width: 36px; height: 36px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; margin-bottom: 12px; background: rgba(88,166,255,0.1);
  }}
  .s-name {{ font-size: 13px; font-weight: 700; color: #f0f6fc; margin-bottom: 6px; line-height: 1.4; }}
  .s-desc {{ font-size: 11.5px; color: #8b949e; line-height: 1.5; }}

  /* ===== 指标网格 ===== */
  .metrics-grid {{
    display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 32px;
  }}
  .metric-card {{
    background: #161b22; border: 1px solid #21262d; border-radius: 10px;
    padding: 16px; text-align: center;
  }}
  .metric-label {{ font-size: 11px; color: #8b949e; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .metric-value {{ font-size: 20px; font-weight: 700; color: #f0f6fc; font-variant-numeric: tabular-nums; }}
  .metric-value.positive {{ color: #f85149; }}
  .metric-value.neutral   {{ color: #58a6ff; }}

  /* ===== 图表区域 ===== */
  .chart-section {{ margin-bottom: 28px; }}
  .section-title {{
    font-size: 15px; font-weight: 600; color: #f0f6fc; margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
  }}
  .section-title::before {{
    content: ''; width: 4px; height: 16px; background: #58a6ff; border-radius: 2px;
  }}
  .chart-box {{
    background: #161b22; border: 1px solid #21262d; border-radius: 12px; padding: 20px;
  }}
  .chart-row {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 28px;
  }}

  /* ===== 对比表格 ===== */
  .compare-table {{ width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13px; }}
  .compare-table th {{
    background: #21262d; color: #8b949e; font-weight: 600;
    padding: 12px 16px; text-align: left; font-size: 12px;
    text-transform: uppercase; letter-spacing: 0.5px;
  }}
  .compare-table th:first-child {{ border-radius: 8px 0 0 0; }}
  .compare-table th:last-child  {{ border-radius: 0 8px 0 0; }}
  .compare-table td {{ padding: 12px 16px; border-bottom: 1px solid #21262d; color: #e6edf3; transition: background 0.15s; }}
  .compare-table tr:hover td {{ background: rgba(88,166,255,0.04); }}
  .compare-table tr:last-child td {{ border-bottom: none; }}
  .up   {{ color: #f85149; font-weight: 600; }}
  .down {{ color: #3fb950; font-weight: 600; }}
  .tag {{
    display: inline-flex; align-items: center; padding: 2px 8px;
    border-radius: 4px; font-size: 11px; font-weight: 600;
  }}
  .tag-blue   {{ background: rgba(88,166,255,0.12); color: #58a6ff; }}
  .tag-orange {{ background: rgba(210,153,34,0.12);  color: #d29922; }}
  .tag-green  {{ background: rgba(63,185,80,0.12);   color: #3fb950; }}
  .tag-purple {{ background: rgba(188,140,255,0.12); color: #bc8cff; }}

  /* ===== 信息栏 ===== */
  .info-bar {{
    background: rgba(88,166,255,0.06); border: 1px solid rgba(88,166,255,0.2);
    border-radius: 8px; padding: 12px 20px; font-size: 12.5px; color: #8b949e;
    margin-bottom: 28px; display: flex; align-items: center; gap: 8px;
  }}
  .info-bar strong {{ color: #58a6ff; }}

  /* ===== Tab ===== */
  .tab-row {{ display: flex; gap: 8px; margin-bottom: 20px; }}
  .tab-btn {{
    padding: 6px 16px; border-radius: 6px; border: 1px solid #30363d;
    background: transparent; color: #8b949e; font-size: 13px;
    cursor: pointer; transition: all 0.2s; font-family: inherit;
  }}
  .tab-btn:hover {{ border-color: #58a6ff; color: #58a6ff; }}
  .tab-btn.active {{ background: #58a6ff; border-color: #58a6ff; color: #0d1117; font-weight: 600; }}

  /* ===== 交易记录 ===== */
  .trade-log {{ max-height: 320px; overflow-y: auto; }}
  .trade-log::-webkit-scrollbar {{ width: 6px; }}
  .trade-log::-webkit-scrollbar-track {{ background: #0d1117; }}
  .trade-log::-webkit-scrollbar-thumb {{ background: #30363d; border-radius: 3px; }}

  /* ===== 免责声明 ===== */
  .disclaimer {{
    background: rgba(210,153,34,0.06); border: 1px solid rgba(210,153,34,0.2);
    border-radius: 8px; padding: 14px 20px; font-size: 12px; color: #8b949e;
    margin-top: 32px; line-height: 1.6;
  }}
  .disclaimer strong {{ color: #d29922; }}
</style>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <div class="badge">📊 量化策略回测报告</div>
    <h1 class="title">{ma_label}趋势过滤器 × 定投策略</h1>
    <p class="subtitle">
      标的: <span>{ts_code}</span> &nbsp;|&nbsp;
      回测区间: <span>{date_range}</span> &nbsp;|&nbsp;
      每期基础金额: <span>¥{monthly_amount:,.0f}</span> &nbsp;|&nbsp;
      定投周期: <span>每月第一交易日</span>
    </p>
  </div>
</div>

<div class="main">

  <div class="info-bar">
    💡 <strong>策略核心逻辑：</strong>
    以{ma_label}（{ma_period}日移动均线）为趋势过滤器，判断市场处于上升还是下跌趋势，
    动态调整每月定投金额——低位加大投入摊薄成本，高位减少或保持投入控制风险。
  </div>

  <!-- 策略卡片 -->
  <div class="strategy-cards" id="strategyCards">
    <div class="strategy-card active" style="--color:#58a6ff" onclick="selectStrategy(0)">
      <div class="s-icon">📅</div>
      <div class="s-name">普通定投</div>
      <div class="s-desc">忽略趋势信号，每月固定投入¥{monthly_amount:,.0f}，不做任何调整，作为基准对照组</div>
    </div>
    <div class="strategy-card" style="--color:#f85149" onclick="selectStrategy(1)">
      <div class="s-icon">🔥</div>
      <div class="s-name">趋势加倍定投</div>
      <div class="s-desc">收盘 &lt; {ma_label} → 2倍投入；收盘 ≥ {ma_label} → 正常投入</div>
    </div>
    <div class="strategy-card" style="--color:#3fb950" onclick="selectStrategy(2)">
      <div class="s-icon">⛔</div>
      <div class="s-name">趋势暂停定投</div>
      <div class="s-desc">收盘 &lt; {ma_label} → 暂停当月；收盘 ≥ {ma_label} → 正常投入，规避下跌趋势</div>
    </div>
    <div class="strategy-card" style="--color:#bc8cff" onclick="selectStrategy(3)">
      <div class="s-icon">⚡</div>
      <div class="s-name">趋势分级定投</div>
      <div class="s-desc">按价格偏离{ma_label}程度动态调整：上方≥5%→0.5x；上方→1x；下方5%→1.5x；下方10%→2x；下方&gt;10%→3x</div>
    </div>
  </div>

  <!-- 指标卡片 -->
  <div id="metricsGrid" class="metrics-grid"></div>

  <!-- 价格 + MA -->
  <div class="chart-section">
    <div class="section-title">价格走势 & {ma_label}</div>
    <div class="chart-box"><div id="chartPrice" style="height:320px;"></div></div>
  </div>

  <!-- 市值 + 四策略对比 -->
  <div class="chart-row">
    <div class="chart-section" style="margin-bottom:0">
      <div class="section-title">组合市值 vs 累计投入</div>
      <div class="chart-box"><div id="chartNav" style="height:280px;"></div></div>
    </div>
    <div class="chart-section" style="margin-bottom:0">
      <div class="section-title">四策略收益率对比</div>
      <div class="chart-box"><div id="chartCompare" style="height:280px;"></div></div>
    </div>
  </div>

  <div style="height:28px;"></div>

  <!-- 每月投入 -->
  <div class="chart-section">
    <div class="section-title">每月实际投入金额（当前策略）</div>
    <div class="chart-box"><div id="chartMonthly" style="height:220px;"></div></div>
  </div>

  <!-- 综合对比表 -->
  <div class="chart-section">
    <div class="section-title">四策略综合对比</div>
    <div class="chart-box">
      <table class="compare-table">
        <thead>
          <tr>
            <th>策略名称</th><th>总投入</th><th>最终市值</th><th>绝对收益</th>
            <th>总收益率</th><th>年化收益</th><th>最大回撤</th><th>买入次数</th><th>暂停次数</th>
          </tr>
        </thead>
        <tbody id="compareTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- 交易明细 -->
  <div class="chart-section">
    <div class="section-title">交易明细（当前策略）</div>
    <div class="chart-box">
      <div class="tab-row" id="tradeTabRow">
        <button class="tab-btn active" onclick="filterTrade('all')">全部</button>
        <button class="tab-btn" onclick="filterTrade('buy')">买入记录</button>
        <button class="tab-btn" onclick="filterTrade('skip')">暂停记录</button>
      </div>
      <div class="trade-log">
        <table class="compare-table" id="tradeTable">
          <thead>
            <tr>
              <th>日期</th><th>收盘价</th><th>{ma_label}</th><th>相对位置</th>
              <th>本期投入</th><th>操作</th><th>累计投入</th><th>组合市值</th>
            </tr>
          </thead>
          <tbody id="tradeTableBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="disclaimer">
    <strong>⚠️ 风险提示：</strong>
    本报告仅为历史数据回测分析，不构成任何投资建议。历史业绩不代表未来表现。
    定投策略可降低投资风险，但无法保证盈利。投资有风险，入市需谨慎。
  </div>

</div><!-- /main -->

<script>
const RESULTS  = {results_json};
const PRICE_MA30 = {price_json};
const MA_LABEL = '{ma_label}';

const COLORS  = ['#58a6ff', '#f85149', '#3fb950', '#bc8cff'];
const TAGS    = ['tag-blue', 'tag-orange', 'tag-green', 'tag-purple'];
const LABELS  = ['普通定投', '趋势加倍定投', '趋势暂停定投', '趋势分级定投'];

let currentStrategy = 0;
let currentFilter   = 'all';
let chartPrice, chartNav, chartMonthly, chartCompare;

window.addEventListener('load', () => {{
  initChartPrice();
  initChartCompare();
  renderMetrics(0);
  renderStrategy(0);
  renderCompareTable();
}});

function selectStrategy(idx) {{
  currentStrategy = idx;
  document.querySelectorAll('.strategy-card').forEach((c, i) => c.classList.toggle('active', i === idx));
  renderMetrics(idx);
  renderStrategy(idx);
}}

function renderMetrics(idx) {{
  const r = RESULTS[idx];
  const profit = r.final_value - r.total_invested;
  document.getElementById('metricsGrid').innerHTML = `
    <div class="metric-card">
      <div class="metric-label">总投入金额</div>
      <div class="metric-value neutral">¥${{(r.total_invested/10000).toFixed(2)}}万</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">最终市值</div>
      <div class="metric-value">¥${{(r.final_value/10000).toFixed(2)}}万</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">绝对盈亏</div>
      <div class="metric-value ${{profit>=0?'positive up':'down'}}">
        ${{profit>=0?'+':''}}¥${{profit.toLocaleString('zh-CN',{{maximumFractionDigits:0}})}}
      </div>
    </div>
    <div class="metric-card">
      <div class="metric-label">年化收益率</div>
      <div class="metric-value ${{r.annual_return>=0?'positive':'down'}}">${{r.annual_return>=0?'+':''}}${{r.annual_return}}%</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">最大回撤</div>
      <div class="metric-value down">-${{r.max_drawdown}}%</div>
    </div>`;
}}

function initChartPrice() {{
  chartPrice = echarts.init(document.getElementById('chartPrice'));
  chartPrice.setOption({{
    backgroundColor: 'transparent',
    tooltip: {{ trigger: 'axis', backgroundColor: '#21262d', borderColor: '#30363d', textStyle: {{ color: '#e6edf3', fontSize: 12 }} }},
    legend: {{ data: ['{ts_code}', MA_LABEL], textStyle: {{ color: '#8b949e' }}, top: 0 }},
    grid: {{ top: 36, bottom: 40, left: 60, right: 20 }},
    xAxis: {{
      type: 'category', data: PRICE_MA30.map(d=>d[0]),
      axisLine: {{ lineStyle: {{ color: '#30363d' }} }},
      axisLabel: {{ color: '#8b949e', fontSize: 11 }},
      splitLine: {{ show: false }},
    }},
    yAxis: {{
      type: 'value',
      axisLabel: {{ color: '#8b949e', fontSize: 11, formatter: v => '¥'+v.toFixed(2) }},
      splitLine: {{ lineStyle: {{ color: '#21262d', type: 'dashed' }} }},
    }},
    dataZoom: [{{ type: 'slider', bottom: 4, height: 18, borderColor: '#30363d',
      fillerColor: 'rgba(88,166,255,0.1)', handleStyle: {{ color: '#58a6ff' }} }}],
    series: [
      {{
        name: '{ts_code}', type: 'line', data: PRICE_MA30.map(d=>d[1]),
        lineStyle: {{ color: '#58a6ff', width: 1.5 }}, symbol: 'none',
        areaStyle: {{ color: {{ type:'linear',x:0,y:0,x2:0,y2:1,
          colorStops:[{{offset:0,color:'rgba(88,166,255,0.15)'}},{{offset:1,color:'rgba(88,166,255,0)'}}] }} }},
      }},
      {{
        name: MA_LABEL, type: 'line', data: PRICE_MA30.map(d=>d[2]),
        lineStyle: {{ color: '#f85149', width: 1.5, type: 'dashed' }}, symbol: 'none',
      }},
    ],
  }});
}}

function renderStrategy(idx) {{
  const r = RESULTS[idx];
  if (!chartNav) chartNav = echarts.init(document.getElementById('chartNav'));
  chartNav.setOption({{
    backgroundColor: 'transparent',
    tooltip: {{
      trigger: 'axis', backgroundColor: '#21262d', borderColor: '#30363d',
      textStyle: {{ color: '#e6edf3', fontSize: 12 }},
      formatter: params => params[0].axisValue + '<br/>' +
        params.map(p=>`<span style="color:${{p.color}}">●</span> ${{p.seriesName}}: ¥${{p.value.toLocaleString('zh-CN',{{maximumFractionDigits:0}})}}`).join('<br/>'),
    }},
    legend: {{ data: ['组合市值','累计投入'], textStyle: {{ color: '#8b949e' }}, top: 0 }},
    grid: {{ top: 36, bottom: 10, left: 65, right: 16 }},
    xAxis: {{
      type: 'category', data: r.nav_series.map(d=>d[0]),
      axisLine: {{ lineStyle: {{ color: '#30363d' }} }},
      axisLabel: {{ color: '#8b949e', fontSize: 10 }},
    }},
    yAxis: {{
      type: 'value',
      axisLabel: {{ color: '#8b949e', fontSize: 10, formatter: v => (v/10000).toFixed(1)+'万' }},
      splitLine: {{ lineStyle: {{ color: '#21262d', type: 'dashed' }} }},
    }},
    series: [
      {{
        name: '组合市值', type: 'line', data: r.nav_series.map(d=>d[1]),
        lineStyle: {{ color: COLORS[idx], width: 2 }}, symbol: 'none',
        areaStyle: {{ color: {{ type:'linear',x:0,y:0,x2:0,y2:1,
          colorStops:[{{offset:0,color:COLORS[idx]+'30'}},{{offset:1,color:COLORS[idx]+'00'}}] }} }},
      }},
      {{
        name: '累计投入', type: 'line', data: r.nav_series.map(d=>d[2]),
        lineStyle: {{ color: '#8b949e', width: 1.5, type: 'dashed' }}, symbol: 'none',
      }},
    ],
  }});
  renderMonthlyChart(idx);
  renderTradeTable(idx, currentFilter);
}}

function renderMonthlyChart(idx) {{
  if (!chartMonthly) chartMonthly = echarts.init(document.getElementById('chartMonthly'));
  const r = RESULTS[idx];
  const amounts = r.trade_log.map(t => t.amount);
  chartMonthly.setOption({{
    backgroundColor: 'transparent',
    tooltip: {{ trigger: 'axis', backgroundColor: '#21262d', borderColor: '#30363d', textStyle: {{ color: '#e6edf3', fontSize: 12 }} }},
    grid: {{ top: 20, bottom: 40, left: 55, right: 16 }},
    xAxis: {{
      type: 'category', data: r.trade_log.map(t=>t.date.slice(0,7)),
      axisLine: {{ lineStyle: {{ color: '#30363d' }} }},
      axisLabel: {{ color: '#8b949e', fontSize: 10, rotate: 45, interval: 2 }},
    }},
    yAxis: {{
      type: 'value',
      axisLabel: {{ color: '#8b949e', fontSize: 10, formatter: v => '¥'+v }},
      splitLine: {{ lineStyle: {{ color: '#21262d', type: 'dashed' }} }},
    }},
    series: [{{
      name: '投入金额', type: 'bar', barMaxWidth: 12,
      data: amounts.map((a, i) => ({{
        value: a,
        itemStyle: {{
          color: a===0?'#30363d':(a>1000?'#f85149':(a<1000?'#3fb950':COLORS[idx])),
          borderRadius: [3,3,0,0],
        }},
      }})),
    }}],
  }});
}}

function initChartCompare() {{
  chartCompare = echarts.init(document.getElementById('chartCompare'));
  chartCompare.setOption({{
    backgroundColor: 'transparent',
    tooltip: {{
      trigger: 'axis', backgroundColor: '#21262d', borderColor: '#30363d',
      textStyle: {{ color: '#e6edf3', fontSize: 12 }},
      formatter: params => params[0].axisValue + '<br/>' +
        params.map(p => `<span style="color:${{p.color}}">●</span> ${{p.seriesName}}: ` +
          `<span style="color:${{p.value[1]>=0?'#f85149':'#3fb950'}}">${{p.value[1]>=0?'+':''}}${{p.value[1]}}%</span>`
        ).join('<br/>'),
    }},
    legend: {{ data: LABELS, textStyle: {{ color: '#8b949e', fontSize: 11 }}, top: 0, itemWidth: 14, itemHeight: 3 }},
    grid: {{ top: 44, bottom: 10, left: 52, right: 16 }},
    xAxis: {{
      type: 'time',
      axisLine: {{ lineStyle: {{ color: '#30363d' }} }},
      axisLabel: {{ color: '#8b949e', fontSize: 10 }},
      splitLine: {{ show: false }},
    }},
    yAxis: {{
      type: 'value',
      axisLabel: {{ color: '#8b949e', fontSize: 10, formatter: v => v+'%' }},
      splitLine: {{ lineStyle: {{ color: '#21262d', type: 'dashed' }} }},
    }},
    series: RESULTS.map((r, idx) => ({{
      name: LABELS[idx], type: 'line', symbol: 'none',
      lineStyle: {{ color: COLORS[idx], width: 1.8 }},
      data: r.nav_series.filter(d=>d[2]>0).map(d => [d[0], parseFloat(((d[1]-d[2])/d[2]*100).toFixed(2))]),
    }})),
  }});
}}

function renderCompareTable() {{
  const bestReturn = Math.max(...RESULTS.map(r => r.total_return));
  document.getElementById('compareTableBody').innerHTML = RESULTS.map((r, idx) => {{
    const profit = r.final_value - r.total_invested;
    return `<tr>
      <td><span class="tag ${{TAGS[idx]}}">${{LABELS[idx]}}</span></td>
      <td>¥${{r.total_invested.toLocaleString('zh-CN')}}</td>
      <td>¥${{r.final_value.toLocaleString('zh-CN')}}</td>
      <td class="${{profit>=0?'up':'down'}}">${{profit>=0?'+':''}}¥${{profit.toLocaleString('zh-CN',{{maximumFractionDigits:0}})}}</td>
      <td class="${{r.total_return>=0?'up':'down'}}">${{r.total_return===bestReturn?'🏆 ':''}}${{r.total_return>=0?'+':''}}${{r.total_return}}%</td>
      <td class="${{r.annual_return>=0?'up':'down'}}">${{r.annual_return>=0?'+':''}}${{r.annual_return}}%</td>
      <td class="down">-${{r.max_drawdown}}%</td>
      <td>${{r.invest_count}}</td>
      <td>${{r.skip_count>0?r.skip_count:'—'}}</td>
    </tr>`;
  }}).join('');
}}

function filterTrade(filter) {{
  currentFilter = filter;
  document.querySelectorAll('.tab-btn').forEach(b => {{
    b.classList.toggle('active', b.textContent.includes(filter==='all'?'全部':filter==='buy'?'买入':'暂停'));
  }});
  renderTradeTable(currentStrategy, filter);
}}

function renderTradeTable(idx, filter) {{
  let logs = RESULTS[idx].trade_log;
  if (filter === 'buy')  logs = logs.filter(t => t.amount > 0);
  if (filter === 'skip') logs = logs.filter(t => t.amount === 0);
  document.getElementById('tradeTableBody').innerHTML = logs.map(t => {{
    const above  = t.ma30 ? t.price > t.ma30 : true;
    const pct    = t.ma30 ? ((t.price - t.ma30) / t.ma30 * 100).toFixed(1) : '-';
    const posLabel = above ? `均线上 +${{pct}}%` : `均线下 ${{pct}}%`;
    return `<tr>
      <td>${{t.date}}</td>
      <td>¥${{t.price}}</td>
      <td>${{t.ma30?'¥'+t.ma30:'-'}}</td>
      <td class="${{above?'up':'down'}}">${{posLabel}}</td>
      <td>${{t.amount>0?'¥'+t.amount.toLocaleString():'-'}}</td>
      <td>${{t.amount===0
        ?'<span style="color:#8b949e">暂停</span>'
        :t.amount>1000
          ?'<span class="up">加倍/多投</span>'
          :'<span style="color:'+COLORS[idx]+'">正常投入</span>'}}</td>
      <td>¥${{t.total_invested.toLocaleString()}}</td>
      <td class="${{t.portfolio_value>t.total_invested?'up':'down'}}">¥${{t.portfolio_value.toLocaleString()}}</td>
    </tr>`;
  }}).join('');
}}

window.addEventListener('resize', () => {{
  [chartPrice, chartNav, chartMonthly, chartCompare].forEach(c => c && c.resize());
}});
</script>
</body>
</html>"""
    return html


def main():
    args = parse_args()

    with open(args.results_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    with open(args.price_path, "r", encoding="utf-8") as f:
        price_ma30 = json.load(f)

    # 自动推断日期范围
    start_date = args.start_date
    end_date   = args.end_date
    if not start_date and results:
        try:
            start_date = results[0]["nav_series"][0][0]
            end_date   = results[0]["nav_series"][-1][0]
        except Exception:
            pass

    html = generate_html(
        results, price_ma30,
        ma_period=args.ma_period,
        ts_code=args.ts_code,
        start_date=start_date,
        end_date=end_date,
        monthly_amount=args.monthly_amount,
    )

    output_path = args.output_path
    if not output_path:
        base_dir  = os.path.dirname(args.results_path)
        output_path = os.path.join(base_dir, "ma30_dca_report.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[report] HTML报告已生成: {output_path}")
    return output_path


if __name__ == "__main__":
    main()
