# DataMind 🧠

![Python Version](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://datamind-multi-agent.streamlit.app/)

DataMind 是一个基于 **Streamlit** 和 **LangGraph** 的现代化、企业级自动数据分析平台。通过五大专门调优的 AI Agent 智能协同，DataMind 能够一键完成：**「数据嗅探 → 智能清洗 → EDA 探索 → 领域建模分析 → 洞察报告生成」** 全流程工作模式，极大提升数据分析与洞察提取效率。

> 💡 **项目背景**：传统的数据探索分析（EDA）和 A/B 测试往往需要编写大量重复的 Pandas 代码。本项目利用大语言模型（LLM）的多 Agent 架构能力，将人工分析的最佳实践沉淀入 Pipeline 中，打造了「Human in the Loop」增强的高端 SaaS 分析体验。

---

## 🎯 核心特性 (Features)

*   **🚀 Auto-Pipeline 多 Agent 自动协作**
    基于 LangGraph 的有向无环图 (DAG) 状态机架构，实现了：
    *   `Router Agent`：全局调度与业务场景嗅探。
    *   `Cleaning Agent`：异常值诊断、缺失值填补建议。
    *   `EDA Agent`：自动化探索性数据分析及图表洞察。
    *   `Domain Analyst Agent`：根据识别场景（电商、营销留存等），自动执行 RFM / 队列分析。
    *   `Report Generator`：整合分析结论，生成管理友好的决策报告。
*   **✨ 高级 SaaS 交互与 UI (Glassmorphism & Depth)**
    告别传统 Streamlit 的单调，项目深度定制了光影、圆角、层次化卡片以及微动画（CSS 注入），提供具有“呼吸感”的商业级 UI 体验。
*   **📊 一键动态 Dashboard**
    采用 Plotly 引擎，内置自适应的直方图、漏斗图和群组分析矩阵，保障了良好的数据可视化信息密度。

## ⚙️ 系统架构图 (Architecture)

```mermaid
graph TD
    User([📌 User Data Upload]) --> Router
    subgraph "Multi-Agent System (LangGraph)"
        Router[🤖 Router Agent<br/>判断场景策略]
        Cleaning[🧹 Cleaning Agent<br/>异常处理/规范化]
        EDA[🔍 EDA Agent<br/>分布/相关性探索]
        Analyst[👔 Domain Analyst Agent<br/>特定领域建模]
        Report[📝 Report Agent<br/>洞察报告生成]
        
        Router --> Cleaning
        Cleaning --> EDA
        EDA --> Analyst
        Analyst --> Report
    end
    Report --> Dashboard([📊 Streamlit SaaS UI Visualization])
```

## 📦 快速开始 (Quick Start)

### 1. 环境准备
确保本机已安装 Python 3.11+
```bash
git clone https://github.com/notwulin/Datamind.git
cd datamind

# 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # Windows 为 venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置大模型 API Keys
创建 `.env` 文件并填入您的 LLM 密钥（系统兼容 LangChain 接口接入的大语言模型）：
```env
GOOGLE_API_KEY="your_gemini_api_key"
# 或添加其他模型配置
```

### 3. 运行平台
```bash
streamlit run app.py
```

### 4. Demo 数据体验
在网页启动后，您可以直接从项目自带的 `data/` 目录下上传我们提供的测试数据集 `sample_ecommerce.csv` 体验完整流程。

---

## 📅 版本记录
详细的版本迭代历史请参阅 [CHANGELOG.md](CHANGELOG.md)。

## 📝 许可证 (License)
本项目基于 [MIT License](LICENSE) 协议开源。
