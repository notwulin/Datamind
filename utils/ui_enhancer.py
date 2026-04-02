import streamlit as st

def apply_saas_style():
    """
    全局 SaaS 级 CSS 注入：
    - 原则 1: 统一比例与对齐 (按钮居中、卡片等高、columns 垂直居中)
    - 原则 2: 底色分离与空间深度 (浅灰底色 + 纯白悬浮卡片)
    - 原则 3: 字体微调与 Icon 引导 (弱化标签、强化数值)
    - 原则 4: 模块收纳与状态引导 (空状态虚线容器)
    """
    custom_css = """
        <style>
        /* ─────────────────────────────────────────────────────
           0. 全局字体系统 — Inter (Google Fonts)
           ───────────────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [data-testid="stAppViewContainer"],
        [data-testid="stSidebar"], [data-testid="stHeader"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
        }

        /* ─────────────────────────────────────────────────────
           1. 系统 Chrome 隐藏 (保留侧边栏汉堡按钮)
           ───────────────────────────────────────────────────── */
        #MainMenu {visibility: hidden;}
        header[data-testid="stHeader"] {background: transparent !important;}
        footer {visibility: hidden;}

        /* ─────────────────────────────────────────────────────
           2. [原则 2] 全局底色分离 — 极浅灰呼吸感底板
           ───────────────────────────────────────────────────── */
        [data-testid="stAppViewContainer"] {
            background-color: #F7F9FC !important;
        }

        /* 主内容区约束 */
        [data-testid="block-container"] {
            max-width: 1200px;
            padding-top: 2.5rem;
            padding-bottom: 2rem;
        }

        /* ─────────────────────────────────────────────────────
           3. [原则 1] 侧边栏瘦身 + 导航行高优化
           ───────────────────────────────────────────────────── */
        [data-testid="stSidebar"][aria-expanded="true"] {
            min-width: 260px !important;
            max-width: 260px !important;
        }
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] [data-testid="stSidebarNav"] li {
            line-height: 2.2 !important;
        }

        /* ─────────────────────────────────────────────────────
           4. [原则 1+2] 卡片统一规范 — 等高 + 悬浮 + 圆角
              针对 st.container(border=True) 的渲染容器
           ───────────────────────────────────────────────────── */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF !important;
            border-radius: 12px !important;
            border: 1px solid #F0F0F0 !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05),
                        0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
            padding: 1.5rem !important;
            transition: box-shadow 0.2s ease, transform 0.15s ease;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            box-shadow: 0 8px 16px -4px rgba(0, 0, 0, 0.08),
                        0 4px 8px -2px rgba(0, 0, 0, 0.04) !important;
            transform: translateY(-1px);
        }

        /* ─────────────────────────────────────────────────────
           5. [原则 1] 所有 st.columns 内的内容垂直居中
           ───────────────────────────────────────────────────── */
        [data-testid="stHorizontalBlock"] {
            align-items: center !important;
        }

        /* ─────────────────────────────────────────────────────
           6. [原则 2+3] KPI Metric 样式 — 弱化标签、强化数值
           ───────────────────────────────────────────────────── */
        [data-testid="stMetricLabel"] {
            color: #6B7280 !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }
        [data-testid="stMetricValue"] {
            color: #111827 !important;
            font-size: 1.65rem !important;
            font-weight: 700 !important;
            line-height: 1.3;
        }
        /* delta 值微调 */
        [data-testid="stMetricDelta"] {
            font-size: 0.78rem !important;
        }

        /* ─────────────────────────────────────────────────────
           7. [原则 1] 按钮精致化 — 去除巨物感
           ───────────────────────────────────────────────────── */
        button[kind="primary"] {
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 0.88rem !important;
            padding: 0.5rem 1.5rem !important;
            letter-spacing: 0.01em;
            transition: all 0.2s ease !important;
        }
        button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(46, 104, 237, 0.3) !important;
        }
        button[kind="secondary"] {
            border-radius: 8px !important;
            font-weight: 500 !important;
            border: 1px solid #E5E7EB !important;
            background-color: #FFFFFF !important;
            transition: all 0.15s ease !important;
        }
        button[kind="secondary"]:hover {
            border-color: #2E68ED !important;
            color: #2E68ED !important;
        }

        /* ─────────────────────────────────────────────────────
           8. [原则 4] 空状态虚线收纳区
           ───────────────────────────────────────────────────── */
        .empty-state-box {
            border: 2px dashed #D1D5DB;
            background: linear-gradient(135deg, #FAFBFF 0%, #F7F9FC 100%);
            border-radius: 16px;
            padding: 3rem 2rem;
            text-align: center;
            margin: 0.5rem 0 1.5rem 0;
        }
        .empty-state-box h3 {
            color: #111827;
            font-weight: 600;
            font-size: 1.25rem;
            margin: 0.75rem 0 0.5rem 0;
        }
        .empty-state-box p {
            color: #6B7280;
            font-size: 0.95rem;
            margin: 0 0 1rem 0;
            line-height: 1.6;
        }
        .empty-state-box .agent-chips {
            display: flex;
            gap: 0.5rem;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 1rem;
        }
        .empty-state-box .agent-chip {
            font-size: 0.8rem;
            color: #4B5563;
            background: #FFFFFF;
            padding: 0.35rem 0.85rem;
            border-radius: 20px;
            border: 1px solid #E5E7EB;
            white-space: nowrap;
        }

        /* ─────────────────────────────────────────────────────
           9. 各种卡片载体（Chat/状态/输入框）彻底消灭扁平感
           ───────────────────────────────────────────────────── */
        [data-testid="stChatMessage"] {
            background-color: #FFFFFF !important;
            border-radius: 12px !important;
            border: 1px solid #F0F0F0 !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
            padding: 1.5rem !important;
            margin-bottom: 1rem;
        }

        /* 状态卡片 (st.info, st.success 等) 浮出底色并在内部保留适当标记颜色 */
        [data-testid="stAlert"] {
            background-color: #FFFFFF !important;
            border-radius: 12px !important;
            border: 1px solid #F0F0F0 !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
            padding: 1.5rem !important;
        }



        /* ─────────────────────────────────────────────────────
          10. Expander 圆角化
           ───────────────────────────────────────────────────── */
        [data-testid="stExpander"] {
            border-radius: 10px !important;
            border: 1px solid #E5E7EB !important;
            overflow: hidden;
        }

        /* ─────────────────────────────────────────────────────
          11. Tab 条目间距
           ───────────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 8px 16px;
        }

        /* ─────────────────────────────────────────────────────
          12. File uploader 风格化
           ───────────────────────────────────────────────────── */
        [data-testid="stFileUploader"] section {
            border: 2px dashed #D1D5DB !important;
            border-radius: 12px !important;
            padding: 1rem !important;
            background: #FFFFFF !important;
        }
        [data-testid="stFileUploader"] section:hover {
            border-color: #2E68ED !important;
        }

        /* ─────────────────────────────────────────────────────
          13. 下载链接居中样式
           ───────────────────────────────────────────────────── */
        .download-link-center {
            text-align: center;
            margin-top: 1.5rem;
        }
        .download-link-center a {
            color: #6B7280;
            text-decoration: none;
            font-size: 0.85rem;
            transition: color 0.2s;
        }
        .download-link-center a:hover {
            color: #2E68ED;
        }

        </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
