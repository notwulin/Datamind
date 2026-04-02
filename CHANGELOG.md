# Changelog

All notable changes to the `DataMind` project will be documented in this file.

## [v3.0.0] - 2026-04-02
### Added
- **LangGraph Multi-Agent Architecture**: 重构底层分析逻辑，拆分为 Cleaning, EDA, Analyst, AB Test, Router 五个独立 Agent。
- **Auto-Pipeline**: 新增 `agents/pipeline.py` 实现图（Graph）状态驱动的一键式自动数据分析。
- **SaaS UI Rework**: 引入基于光影和深度的全局 CSS 注入（`utils/ui_enhancer.py`），全面提升面板、按钮和布局的商业级质感。
- **Sample Data**: 增加 `data/sample_ecommerce.csv` 帮助快速上手和本地测试。

### Changed
- 迁移核心数据存储机制，引入 `session_state` 同步逻辑以适配后端异步图计算机制。

## [v2.1.0] - 2026-03-20
### Added
- 支持多页应用架构 (`pages/` 模块化组织)。
- A/B 测试专用页面上线，支持频率测试、均值检验及功效计算。
- 高级域分析：新增 RFM、LTV、队列分析模块的支持。

## [v1.5.0] - 2026-02-15
### Added
- 基础的 EDA 探索能力及相关性分析。
- 采用 Plotly 丰富了数据可视化展现，支持散点、直方等动态交互统计图。
- 简单的缺失值、重复值一键概览与数据状态评估评分卡。

## [v1.0.0] - 2026-01-10
- **初始化版本**: 实现了单体结构的 Streamlit 数据上传、解析、与简易问答交互的基础原型（MVP）。
