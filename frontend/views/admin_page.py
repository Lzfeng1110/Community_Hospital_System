"""后台管理页面：文件上传、知识库管理、向量库重建。"""

from __future__ import annotations

import streamlit as st

from backend.config import ADMIN_PASSWORD, MODULES
from backend.knowledge_manager import (
    save_uploaded_file,
    delete_file,
    list_files,
    get_stats,
    clear_vector_store,
)
from backend.rag_engine import rebuild_vector_store, invalidate_cache


def _check_login() -> bool:
    if st.session_state.get("admin_logged_in"):
        return True
    st.markdown("## 🔐 管理员登录")
    with st.form("login_form"):
        pwd = st.text_input("请输入管理员密码", type="password")
        submitted = st.form_submit_button("登录")
        if submitted:
            if pwd == ADMIN_PASSWORD:
                st.session_state["admin_logged_in"] = True
                st.rerun()
            else:
                st.error("密码错误，请重试。")
    return False


def render_admin_page() -> None:
    if not _check_login():
        return

    col_title, col_logout = st.columns([8, 1])
    with col_title:
        st.markdown("## 🗂️ 知识库后台管理")
    with col_logout:
        if st.button("退出登录"):
            st.session_state["admin_logged_in"] = False
            st.rerun()

    # ── 统计概览 ────────────────────────────────────────────────
    stats = get_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("知识库文件总数", stats["total_files"])
    c2.metric("总占用空间(MB)", stats["total_size_mb"])
    c3.metric("覆盖模块数", len(stats["by_module"]))

    st.divider()

    # ── 上传文件 ────────────────────────────────────────────────
    st.markdown("### 📤 上传知识文件")
    st.caption('支持 PDF、Word(.docx)、TXT 格式，上传后需点击"重建向量库"生效。')

    upload_module = st.selectbox(
        "选择所属模块",
        options=[k for k in MODULES if k != "all"],
        format_func=lambda k: MODULES[k],
        key="upload_module",
    )

    uploaded_files = st.file_uploader(
        "选择文件（可多选）",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="file_uploader",
    )

    if uploaded_files:
        col_upload, col_rebuild = st.columns(2)
        with col_upload:
            if st.button("💾 保存文件", type="primary", use_container_width=True):
                saved = []
                for f in uploaded_files:
                    try:
                        path = save_uploaded_file(f, upload_module)
                        saved.append(f.name)
                    except Exception as e:
                        st.error(f"保存 {f.name} 失败：{e}")
                if saved:
                    st.success(f"成功保存 {len(saved)} 个文件：{', '.join(saved)}")
                    invalidate_cache(upload_module)

        with col_rebuild:
            if st.button("🔄 保存并重建向量库", type="primary", use_container_width=True):
                saved = []
                for f in uploaded_files:
                    try:
                        save_uploaded_file(f, upload_module)
                        saved.append(f.name)
                    except Exception as e:
                        st.error(f"保存 {f.name} 失败：{e}")
                if saved:
                    with st.spinner("正在重建向量库，请稍候..."):
                        invalidate_cache(upload_module)
                        clear_vector_store(upload_module)
                        msg = rebuild_vector_store(upload_module)
                    st.success(msg)

    st.divider()

    # ── 文件列表 ────────────────────────────────────────────────
    st.markdown("### 📋 知识库文件列表")

    filter_module = st.selectbox(
        "筛选模块",
        options=["all"] + [k for k in MODULES if k != "all"],
        format_func=lambda k: MODULES[k],
        key="filter_module",
    )

    files = list_files(filter_module)

    if not files:
        st.info("当前知识库为空，请先上传文件。")
    else:
        for file_info in files:
            with st.container(border=True):
                col_info, col_del = st.columns([8, 1])
                with col_info:
                    st.markdown(
                        f"**{file_info['filename']}** "
                        f"· `{file_info['module_name']}` "
                        f"· {file_info['size_kb']} KB"
                    )
                    st.caption(f"上传时间：{file_info['uploaded_at'][:19]}")
                with col_del:
                    if st.button("🗑️", key=f"del_{file_info['path']}", help="删除文件"):
                        delete_file(file_info["path"])
                        invalidate_cache(file_info["module"])
                        clear_vector_store(file_info["module"])
                        st.success(f"已删除：{file_info['filename']}")
                        st.rerun()

    st.divider()

    # ── 向量库管理 ────────────────────────────────────────────────
    st.markdown("### ⚙️ 向量库管理")
    st.caption("当手动修改文件或文件内容变更后，需手动重建向量库。")

    rebuild_module = st.selectbox(
        "选择重建范围",
        options=["all"] + [k for k in MODULES if k != "all"],
        format_func=lambda k: MODULES[k],
        key="rebuild_module",
    )

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("🔄 重建向量库", use_container_width=True, type="primary"):
            with st.spinner("重建中，文件较多时需要数分钟，请耐心等待..."):
                invalidate_cache(rebuild_module)
                clear_vector_store(rebuild_module)
                msg = rebuild_vector_store(rebuild_module)
            st.success(msg)

    with col_r2:
        if st.button("🧹 仅清空缓存（不重建）", use_container_width=True):
            invalidate_cache(rebuild_module)
            clear_vector_store(rebuild_module)
            st.success("缓存已清空，下次查询时将自动重建。")
