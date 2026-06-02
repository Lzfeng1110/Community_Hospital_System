"""后台管理页面：知识库管理、首页图片、工作人员档案。"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from backend.config import ADMIN_PASSWORD, MODULES
from backend.knowledge_manager import (
    save_uploaded_file,
    delete_file,
    list_files,
    get_stats,
    clear_vector_store,
)
from backend.media_manager import (
    save_hospital_image,
    list_hospital_images,
    delete_hospital_image,
    update_image_caption,
    move_image,
    add_staff_member,
    list_staff,
    update_staff_member,
    delete_staff_member,
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


# ── 知识库管理 Tab ────────────────────────────────────────────────────

def _render_knowledge_tab() -> None:
    stats = get_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("知识库文件总数", stats["total_files"])
    c2.metric("总占用空间(MB)", stats["total_size_mb"])
    c3.metric("覆盖模块数", len(stats["by_module"]))

    st.divider()
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
                        save_uploaded_file(f, upload_module)
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


# ── 首页图片 Tab ─────────────────────────────────────────────────────

def _render_images_tab() -> None:
    st.markdown("### 📤 上传医院图片")
    st.caption("支持 JPG、PNG、WEBP 格式，图片按列表顺序显示在首页轮播图中，可上移/下移调整顺序。")

    uploaded_imgs = st.file_uploader(
        "选择图片（可多选）",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="hospital_img_uploader",
    )
    caption_input = st.text_input(
        "统一说明文字（可选）",
        placeholder="例：门诊大楼外景",
        key="img_caption_input",
    )
    if uploaded_imgs:
        if st.button("💾 保存图片", type="primary"):
            for f in uploaded_imgs:
                try:
                    save_hospital_image(f, caption_input)
                except Exception as e:
                    st.error(f"保存 {f.name} 失败：{e}")
            st.success(f"成功上传 {len(uploaded_imgs)} 张图片")
            st.rerun()

    st.divider()
    st.markdown("### 📋 已上传图片")

    images = list_hospital_images()
    if not images:
        st.info("尚未上传任何图片。")
        return

    for i, img in enumerate(images):
        with st.container(border=True):
            col_img, col_info = st.columns([3, 7])
            with col_img:
                st.image(Path(img["path"]).read_bytes(), use_container_width=True)
            with col_info:
                st.markdown(f"**{img['filename']}**")
                st.caption(f"上传时间：{img['uploaded_at'][:19]}")

                new_caption = st.text_input(
                    "图片说明",
                    value=img.get("caption", ""),
                    key=f"cap_{img['filename']}",
                    placeholder="为这张图片添加说明文字",
                )
                col_save, col_up, col_down, col_del = st.columns(4)
                with col_save:
                    if st.button("💾 保存说明", key=f"save_cap_{i}", use_container_width=True):
                        update_image_caption(img["filename"], new_caption)
                        st.success("已保存")
                        st.rerun()
                with col_up:
                    disabled_up = i == 0
                    if st.button("⬆️ 上移", key=f"up_{i}", use_container_width=True, disabled=disabled_up):
                        move_image(img["filename"], -1)
                        st.rerun()
                with col_down:
                    disabled_down = i == len(images) - 1
                    if st.button("⬇️ 下移", key=f"down_{i}", use_container_width=True, disabled=disabled_down):
                        move_image(img["filename"], 1)
                        st.rerun()
                with col_del:
                    if st.button("🗑️ 删除", key=f"del_img_{i}", use_container_width=True):
                        delete_hospital_image(img["filename"])
                        st.success("已删除")
                        st.rerun()


# ── 工作人员 Tab ─────────────────────────────────────────────────────

def _render_staff_tab() -> None:
    st.markdown("### ➕ 添加工作人员")

    with st.form("add_staff_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("姓名 *", placeholder="例：张三")
            title = st.text_input("职称 *", placeholder="例：主任医师、全科医生、护士长")
        with col2:
            department = st.text_input("科室 / 部门 *", placeholder="例：全科医疗科")
            photo = st.file_uploader("照片（可选，建议正方形）", type=["jpg", "jpeg", "png"])
        intro = st.text_area(
            "个人简介 *",
            placeholder="请输入工作经历、专业特长、服务理念等...",
            height=100,
        )
        if st.form_submit_button("➕ 添加", type="primary"):
            if not name or not title or not department or not intro:
                st.error("请填写所有必填项（姓名、职称、科室、简介）。")
            else:
                add_staff_member(name, title, department, intro, photo)
                st.success(f"成功添加：{name}")
                st.rerun()

    st.divider()
    st.markdown("### 📋 工作人员列表")

    staff = list_staff()
    if not staff:
        st.info("尚未添加任何工作人员。")
        return

    for member in staff:
        with st.expander(
            f"👤 **{member['name']}** — {member['title']} · {member['department']}"
        ):
            col_photo, col_form = st.columns([2, 5])
            with col_photo:
                if member.get("photo_path"):
                    st.image(Path(member["photo_path"]).read_bytes(), width=130)
                else:
                    st.markdown(
                        '<div style="font-size:4rem;text-align:center;padding:8px;">👤</div>',
                        unsafe_allow_html=True,
                    )
            with col_form:
                with st.form(f"edit_staff_{member['id']}"):
                    new_name = st.text_input("姓名", value=member["name"])
                    new_title = st.text_input("职称", value=member["title"])
                    new_dept = st.text_input("科室/部门", value=member["department"])
                    new_intro = st.text_area("个人简介", value=member["intro"], height=90)
                    new_photo = st.file_uploader(
                        "更换照片",
                        type=["jpg", "jpeg", "png"],
                        key=f"photo_{member['id']}",
                    )
                    col_save, col_del = st.columns(2)
                    with col_save:
                        if st.form_submit_button("💾 保存修改", type="primary", use_container_width=True):
                            update_staff_member(
                                member["id"], new_name, new_title, new_dept, new_intro, new_photo
                            )
                            st.success("已保存")
                            st.rerun()
                    with col_del:
                        if st.form_submit_button("🗑️ 删除此人", use_container_width=True):
                            delete_staff_member(member["id"])
                            st.success("已删除")
                            st.rerun()


# ── 入口 ─────────────────────────────────────────────────────────────

def render_admin_page() -> None:
    if not _check_login():
        return

    col_title, col_logout = st.columns([8, 1])
    with col_title:
        st.markdown("## 🗂️ 后台管理")
    with col_logout:
        if st.button("退出登录"):
            st.session_state["admin_logged_in"] = False
            st.rerun()

    tab_kb, tab_images, tab_staff = st.tabs(["📚 知识库管理", "🖼️ 首页图片", "👨‍⚕️ 工作人员"])

    with tab_kb:
        _render_knowledge_tab()
    with tab_images:
        _render_images_tab()
    with tab_staff:
        _render_staff_tab()
