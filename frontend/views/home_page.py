"""首页：欢迎横幅、医院轮播图、医护团队介绍。"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from backend.media_manager import list_hospital_images, list_staff


def _file_to_b64(path: str) -> tuple[str, str]:
    suffix = Path(path).suffix.lower().lstrip(".")
    mime = "jpeg" if suffix in ("jpg", "jpeg") else suffix
    data = base64.b64encode(Path(path).read_bytes()).decode()
    return data, mime


def render_home_page() -> None:
    # ── 欢迎横幅 ─────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="background:linear-gradient(135deg,#e8f4fd 0%,#e8f8f5 100%);
                    border-radius:12px;padding:1.5rem 2rem;margin-bottom:1.5rem;
                    border-left:5px solid #1a7abf;">
            <h3 style="margin:0 0 0.5rem;color:#1a7abf;">欢迎来到大观街道社区卫生服务中心</h3>
            <p style="margin:0;color:#444;line-height:1.8;font-size:0.95rem;">
                我们秉持"以健康为中心"的服务理念，为辖区居民提供基本医疗、公共卫生、
                家庭医生签约、疫苗接种等一站式健康服务。
                智能助手全天候在线，随时解答您的健康与政策咨询。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 医院轮播图 ────────────────────────────────────────────────────────
    images = list_hospital_images()

    if images:
        st.markdown(
            '<h3 style="color:#1a3a5c;margin-bottom:0.8rem;">🖼️ 医院风采</h3>',
            unsafe_allow_html=True,
        )

        if "carousel_idx" not in st.session_state:
            st.session_state.carousel_idx = 0

        idx = st.session_state.carousel_idx % len(images)
        current = images[idx]

        b64, mime = _file_to_b64(current["path"])
        caption_bar = (
            f'<div style="position:absolute;bottom:0;left:0;right:0;'
            f'background:rgba(0,0,0,0.48);color:white;padding:10px 18px;'
            f'font-size:0.92rem;">{current["caption"]}</div>'
            if current.get("caption")
            else ""
        )
        st.markdown(
            f"""
            <div style="position:relative;border-radius:12px;overflow:hidden;
                        box-shadow:0 4px 20px rgba(0,0,0,0.14);margin-bottom:6px;">
                <img src="data:image/{mime};base64,{b64}"
                     style="width:100%;max-height:440px;object-fit:cover;display:block;">
                {caption_bar}
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_prev, col_dots, col_next = st.columns([1, 8, 1])
        with col_prev:
            if st.button("◀", key="car_prev", use_container_width=True):
                st.session_state.carousel_idx = (idx - 1) % len(images)
                st.rerun()
        with col_dots:
            dots = "".join(
                f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;'
                f'background:{"#1a7abf" if i == idx else "#c8d8e8"};margin:0 5px;'
                f'transition:background 0.3s;"></span>'
                for i in range(len(images))
            )
            st.markdown(
                f'<div style="text-align:center;padding-top:6px;">{dots}</div>',
                unsafe_allow_html=True,
            )
        with col_next:
            if st.button("▶", key="car_next", use_container_width=True):
                st.session_state.carousel_idx = (idx + 1) % len(images)
                st.rerun()

    # ── 医护团队 ──────────────────────────────────────────────────────────
    staff = list_staff()

    if staff:
        st.markdown("")
        st.markdown(
            '<h3 style="color:#1a3a5c;margin:1.2rem 0 0.8rem;">👨‍⚕️ 医护团队</h3>',
            unsafe_allow_html=True,
        )

        cols_per_row = 3
        for row_start in range(0, len(staff), cols_per_row):
            row = staff[row_start : row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, member in zip(cols, row):
                with col:
                    if member.get("photo_path"):
                        b64, mime = _file_to_b64(member["photo_path"])
                        photo_html = (
                            f'<img src="data:image/{mime};base64,{b64}" '
                            f'style="width:110px;height:110px;border-radius:50%;'
                            f'object-fit:cover;margin:0 auto 12px;display:block;'
                            f'border:3px solid #1a7abf;box-shadow:0 2px 8px rgba(26,122,191,0.25);">'
                        )
                    else:
                        photo_html = (
                            '<div style="width:110px;height:110px;border-radius:50%;'
                            'background:#e0e8f0;margin:0 auto 12px;display:flex;'
                            'align-items:center;justify-content:center;font-size:2.8rem;">'
                            "👤</div>"
                        )

                    st.markdown(
                        f"""
                        <div style="background:white;border-radius:12px;padding:22px 16px 20px;
                                    text-align:center;
                                    box-shadow:0 2px 12px rgba(0,0,0,0.08);
                                    border-top:3px solid #1a7abf;
                                    margin-bottom:4px;">
                            {photo_html}
                            <h4 style="margin:0 0 4px;color:#1a3a5c;font-size:1rem;
                                       font-weight:700;">{member["name"]}</h4>
                            <p style="margin:0 0 3px;color:#1a7abf;font-size:0.82rem;
                                      font-weight:600;">{member["title"]}</p>
                            <p style="margin:0 0 10px;color:#0fa37f;font-size:0.78rem;">
                                {member["department"]}</p>
                            <p style="margin:0;color:#555;font-size:0.82rem;line-height:1.65;
                                      text-align:left;">{member["intro"]}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.markdown("<br>", unsafe_allow_html=True)

    # ── 无内容提示 ───────────────────────────────────────────────────────
    if not images and not staff:
        st.info("首页内容尚未配置。请管理员在【后台管理 → 首页图片 / 工作人员】中添加内容。")

    # ── 快速入口 ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown(
        '<h3 style="color:#1a3a5c;margin-bottom:0.8rem;">🚀 快速入口</h3>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    _quick_card(c1, "💬", "智能问答", "政策 · 疫苗 · 预约 · 公告", "#e8f4fd", "#1a7abf")
    _quick_card(c2, "📞", "联系我们", "0871-66052416", "#e8f8f5", "#0fa37f")
    _quick_card(c3, "🕐", "服务时间", "周一至周日 8:30–17:00", "#fef6e4", "#e67e22")


def _quick_card(col, icon: str, title: str, subtitle: str, bg: str, color: str) -> None:
    with col:
        st.markdown(
            f"""
            <div style="background:{bg};border-radius:10px;padding:18px 16px;
                        text-align:center;border-top:3px solid {color};">
                <div style="font-size:2rem;margin-bottom:6px;">{icon}</div>
                <strong style="color:{color};font-size:0.95rem;">{title}</strong>
                <p style="margin:4px 0 0;font-size:0.82rem;color:#555;">{subtitle}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
