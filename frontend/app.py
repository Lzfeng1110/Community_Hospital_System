"""
昆明市五华区大观街道社区卫生服务中心智能问答系统
入口文件：streamlit run frontend/app.py
"""

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(
    page_title="大观街道社区卫生服务中心 · 智能问答",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义样式
st.markdown(
    """
    <style>
    /* 主色调：医疗蓝绿 */
    :root {
        --primary: #1a7abf;
        --secondary: #0fa37f;
    }

    /* 顶部标题栏 */
    .main-header {
        background: linear-gradient(135deg, #1a7abf 0%, #0fa37f 100%);
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        color: white;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.4rem; }
    .main-header p  { color: rgba(255,255,255,0.85); margin: 0.2rem 0 0; font-size: 0.85rem; }

    /* 聊天气泡优化 */
    .stChatMessage { border-radius: 12px; }

    /* 侧边栏快捷按钮 */
    .stButton > button {
        border-radius: 8px;
        font-size: 0.82rem;
        text-align: left;
    }

    /* 隐藏 Streamlit 默认页脚 */
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# 顶部 Banner
st.markdown(
    """
    <div class="main-header">
        <h1>🏥 昆明市五华区大观街道社区卫生服务中心</h1>
        <p>智能问答助手 · 医保政策 · 疫苗接种 · 预约办事 · 社区通知</p>
    </div>
    """,
    unsafe_allow_html=True,
)

from frontend.components.sidebar import render_sidebar
from frontend.views.chat_page import render_chat_page
from frontend.views.admin_page import render_admin_page
from frontend.views.stats_page import render_stats_page

# 渲染侧边栏，获取当前页面与模块
current_page, current_module = render_sidebar()

# 路由到对应页面
if current_page == "💬 智能问答":
    render_chat_page(current_module)
elif current_page == "🗂️ 后台管理":
    render_admin_page()
elif current_page == "📊 统计分析":
    render_stats_page()
