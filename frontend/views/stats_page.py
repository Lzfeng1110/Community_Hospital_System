"""统计分析页面：高频问题、每日趋势、模块分布。"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from backend.config import ADMIN_PASSWORD, MODULES
from backend.log_manager import (
    get_top_questions,
    get_daily_stats,
    get_module_stats,
    get_recent_logs,
    get_total_count,
)


def _check_login() -> bool:
    if st.session_state.get("admin_logged_in"):
        return True
    st.markdown("## 🔐 管理员登录")
    with st.form("stats_login_form"):
        pwd = st.text_input("请输入管理员密码", type="password")
        submitted = st.form_submit_button("登录")
        if submitted:
            if pwd == ADMIN_PASSWORD:
                st.session_state["admin_logged_in"] = True
                st.rerun()
            else:
                st.error("密码错误，请重试。")
    return False


def render_stats_page() -> None:
    if not _check_login():
        return

    st.markdown("## 📊 咨询统计分析")

    total = get_total_count()
    module_stats = get_module_stats()
    daily_stats = get_daily_stats(30)

    # ── 核心指标 ────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("累计咨询次数", f"{total:,}")
    c2.metric("今日咨询", _today_count(daily_stats))
    c3.metric("活跃模块数", len(module_stats))
    c4.metric("统计周期（天）", 30)

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📈 咨询趋势", "🗂️ 模块分布", "🔥 高频问题", "📋 最近记录"]
    )

    # ── Tab1: 每日趋势 ───────────────────────────────────────────
    with tab1:
        if daily_stats:
            df = pd.DataFrame(daily_stats)
            fig = px.bar(
                df,
                x="date",
                y="total",
                title="近30天每日咨询量",
                labels={"date": "日期", "total": "咨询次数"},
                color="total",
                color_continuous_scale="Blues",
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无咨询记录。")

    # ── Tab2: 模块分布 ───────────────────────────────────────────
    with tab2:
        if module_stats:
            df = pd.DataFrame(module_stats)
            df["module_name"] = df["module"].map(lambda k: MODULES.get(k, k))
            fig = px.pie(
                df,
                names="module_name",
                values="cnt",
                title="各模块咨询占比",
                hole=0.4,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("**各模块咨询量明细**")
            df_show = df[["module_name", "cnt"]].rename(
                columns={"module_name": "模块", "cnt": "咨询次数"}
            )
            st.dataframe(df_show, use_container_width=True, hide_index=True)
        else:
            st.info("暂无数据。")

    # ── Tab3: 高频问题 ───────────────────────────────────────────
    with tab3:
        col_m, col_n = st.columns([3, 1])
        with col_m:
            sel_module = st.selectbox(
                "筛选模块",
                options=["all"] + [k for k in MODULES if k != "all"],
                format_func=lambda k: MODULES[k],
                key="stats_module",
            )
        with col_n:
            top_n = st.number_input("显示条数", min_value=5, max_value=50, value=15, step=5)

        top_qs = get_top_questions(limit=int(top_n), module=sel_module)
        if top_qs:
            df_q = pd.DataFrame(top_qs)
            df_q.index = df_q.index + 1
            df_q.columns = ["问题", "出现次数"]

            fig = px.bar(
                df_q.head(15),
                x="出现次数",
                y="问题",
                orientation="h",
                title="高频咨询问题 TOP 15",
                color="出现次数",
                color_continuous_scale="Reds",
            )
            fig.update_layout(height=max(400, len(df_q.head(15)) * 30), showlegend=False)
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("**完整排名列表**")
            st.dataframe(df_q, use_container_width=True)
        else:
            st.info("暂无咨询记录。")

    # ── Tab4: 最近记录 ───────────────────────────────────────────
    with tab4:
        logs = get_recent_logs(50)
        if logs:
            df_logs = pd.DataFrame(logs)
            df_logs["timestamp"] = df_logs["timestamp"].str[:19]
            df_logs["module"] = df_logs["module"].map(lambda k: MODULES.get(k, k))
            df_logs["duration_s"] = (df_logs["duration_ms"] / 1000).round(2)
            df_logs = df_logs[["timestamp", "module", "question", "duration_s"]].rename(
                columns={
                    "timestamp": "时间",
                    "module": "模块",
                    "question": "问题",
                    "duration_s": "耗时(秒)",
                }
            )
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
        else:
            st.info("暂无咨询记录。")


def _today_count(daily_stats: list[dict]) -> int:
    from datetime import date
    today = date.today().isoformat()
    for row in daily_stats:
        if row.get("date") == today:
            return row.get("total", 0)
    return 0
