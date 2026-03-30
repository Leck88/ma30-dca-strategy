# 📈 MA30 趋势过滤器 × 定投策略 回测工具

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/yourusername/ma30-dca-strategy?style=social)](https://github.com/yourusername/ma30-dca-strategy)

> 用 30 日均线作为趋势过滤器，对定投策略进行增强优化的回测工具。支持四种策略对比，生成交互式 HTML 报告。

---

## ✨ 功能特点

- **四种策略对比回测**：普通定投 vs 趋势加倍 vs 趋势暂停 vs 趋势分级
- **MA30 趋势过滤**：判断价格在均线上下，动态调整投入金额
- **交互式 HTML 报告**：基于 ECharts 5，支持缩放、切换、下钻
- **纯标准库**：仅依赖 Python 内置模块（`json`, `math`, `datetime`），零第三方依赖
- **命令行友好**：支持任意标的、任意均线周期、任意基础金额

---

## 📊 策略说明

| 策略 | 触发条件 | 投入倍数 |
|------|----------|----------|
| 普通定投 | 每月固定投入 | × 1.0 |
| 趋势加倍 | 价格 < MA30 时加倍 | × 2.0 / × 1.0 |
| 趋势暂停 | 价格 > MA30 时暂停 | × 1.0 / × 0.0 |
| 趋势分级 | 按偏离MA30的程度分级 | × 0.5 ~ × 3.0 |

**分级定投档位详情**：

| 价格相对MA30 | 投入倍数 |
|------------|----------|
| 均线上方 ≥ 5% | × 0.5（缩减） |
| 均线上方 0~5% | × 1.0（正常） |
| 均线下方 0~5% | × 1.5（加仓） |
| 均线下方 5~10% | × 2.0（加仓） |
| 均线下方 > 10% | × 3.0（重仓） |

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 无需安装任何第三方库

### 准备数据

数据格式为 JSON 文件，字段包含：`trade_date`, `close`, `open`, `high`, `low`, `vol`（可选）。

示例（Tushare / finance-data-retrieval 导出格式）：

```json
[
  {"trade_date": "20200102", "open": 4.012, "high": 4.050, "low": 3.990, "close": 4.021, "vol": 123456.0},
  {"trade_date": "20200103", "open": 4.025, "high": 4.080, "low": 4.010, "close": 4.065, "vol": 234567.0}
]
```

### Step 1：运行回测

```bash
python scripts/backtest.py \
  --data_path 510300_data.json \
  --output_dir ./output \
  --monthly_amount 1000 \
  --ma_period 30
```

输出：
- `backtest_results.json`：四种策略的完整回测结果
- `price_ma30.json`：价格序列与 MA30 序列

### Step 2：生成报告

```bash
python scripts/generate_report.py \
  --results_path ./output/backtest_results.json \
  --price_path ./output/price_ma30.json \
  --output_path ./output/report.html \
  --ts_code "510300.SH" \
  --monthly_amount 1000 \
  --ma_period 30
```

用浏览器打开 `output/report.html` 即可查看交互式报告。

---

## 📁 目录结构

```
ma30-dca-strategy/
├── README.md                     ← 本文件
├── LICENSE                       ← MIT 开源协议
├── SKILL.md                      ← WorkBuddy Skill 入口
├── scripts/
│   ├── backtest.py               ← 回测引擎（命令行脚本）
│   └── generate_report.py        ← HTML 报告生成器
└── references/
    └── strategy-guide.md         ← 策略原理详细说明
```

---

## 📈 报告预览

交互式 HTML 报告包含：

1. **策略对比卡片** — 点击切换不同策略
2. **核心指标看板** — 总投入、最终市值、盈亏、年化收益、最大回撤
3. **价格 + MA30 走势图** — 支持区间缩放
4. **净值 vs 投入曲线** — 直观展示增值效果
5. **四策略收益率对比** — 动态折线图
6. **每月投入柱状图** — 加倍/正常/暂停 三色区分
7. **策略综合对比表格** — 量化指标一览
8. **交易明细记录** — 可按类型过滤

---

## ⚙️ 参数说明

### backtest.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--data_path` | 行情数据 JSON 文件路径 | 必填 |
| `--output_dir` | 输出目录 | `.`（当前目录） |
| `--monthly_amount` | 每期基础定投金额（元） | `1000` |
| `--ma_period` | 均线周期（交易日数） | `30` |

### generate_report.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--results_path` | 回测结果 JSON 路径 | 必填 |
| `--price_path` | 价格+MA序列 JSON 路径 | 必填 |
| `--output_path` | HTML 输出路径 | 必填 |
| `--ts_code` | 标的代码（展示用） | `510300.SH` |
| `--monthly_amount` | 基础定投金额（展示用） | `1000` |
| `--ma_period` | 均线周期（展示用） | `30` |

---

## 🔌 作为 WorkBuddy Skill 使用

本项目同时是一个 [WorkBuddy](https://www.codebuddy.cn/docs/workbuddy/Overview) Skill，可以直接安装到 WorkBuddy AI 助手中，通过自然语言触发完整工作流。

**安装方式**：将本仓库克隆到 `~/.workbuddy/skills/ma30-dca-strategy/`

**触发词**：定投策略、趋势定投、MA30定投、均线定投、定投回测……

```bash
git clone https://github.com/yourusername/ma30-dca-strategy.git \
  ~/.workbuddy/skills/ma30-dca-strategy
```

安装后，在 WorkBuddy 中直接说：
> "帮我对沪深300ETF做30均线定投回测，月投1000元"

---

## 📝 注意事项

1. **数据来源**：需自行准备标的历史日线数据（推荐使用 Tushare 或其他数据源）
2. **不复权数据**：当前脚本使用不复权价格，如需前复权请在数据获取时处理
3. **MA 冷启动**：前 N-1 个交易日无法计算 MAn，这些日期按普通定投处理
4. **ECharts CDN**：报告使用 CDN 加载 ECharts，预览时需要网络连接

---

## 📄 License

MIT License — 详见 [LICENSE](LICENSE)

---

## 🤝 Contributing

欢迎提 Issue 和 PR！

- 新增策略（如均值回归定投、网格定投）
- 支持更多数据格式（CSV、SQLite）
- 报告 UI 优化

---

⭐ 如果这个工具对你有帮助，请给个 Star！
