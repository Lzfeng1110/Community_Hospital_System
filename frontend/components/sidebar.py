"""侧边栏组件：导航、中心信息、快捷问题。"""

import streamlit as st
from backend.config import CENTER_INFO, MODULES

QUICK_QUESTIONS = {
    "all": [
        "医保报销比例是多少？",
        "如何预约老年人体检？",
        "家庭医生如何签约？",
        "中心的门诊时间是什么？",
    ],
    "policy": [
        "城乡居民医保报销比例？",
        "门诊慢特病如何认定？",
        "家庭医生签约有什么优惠？",
        "异地就医如何备案？",
    ],
    "vaccine": [
        "儿童疫苗接种程序是什么？",
        "新冠疫苗还需要打吗？",
        "60岁以上老人可以接种流感疫苗吗？",
        "宝宝出生后第一针打什么？",
    ],
    "appointment": [
        "如何预约家庭医生？",
        "老年人免费体检包含哪些项目？",
        "门诊时间是几点到几点？",
        "产前检查如何预约？",
    ],
    "notice": [
        "本月有哪些健康活动？",
        "最新社区公告是什么？",
        "近期有免费筛查活动吗？",
        "中心有哪些健康讲座？",
    ],
}


def render_sidebar() -> tuple[str, str]:
    """渲染侧边栏，返回 (当前页面, 当前模块)。"""
    with st.sidebar:
        st.image(
            "https://img.icons8.com/color/96/hospital.png",
            width=60,
        )
        st.markdown(f"### {CENTER_INFO['name']}")
        st.caption(f"📍 {CENTER_INFO['address']}")
        st.caption(f"📞 {CENTER_INFO['phone']}")
        st.caption(f"🕐 {CENTER_INFO['hours']}")

        st.divider()

        page = st.radio(
            "功能导航",
            options=["💬 智能问答", "🗂️ 后台管理", "📊 统计分析"],
            key="nav_page",
        )

        selected_module = "all"
        if page == "💬 智能问答":
            st.divider()
            st.markdown("**选择咨询类别**")
            module_key = st.selectbox(
                "咨询类别",
                options=list(MODULES.keys()),
                format_func=lambda k: MODULES[k],
                key="module_select",
                label_visibility="collapsed",
            )
            selected_module = module_key

            st.divider()
            st.markdown("**快捷问题**")
            for q in QUICK_QUESTIONS.get(module_key, QUICK_QUESTIONS["all"]):
                if st.button(q, key=f"quick_{q[:10]}", use_container_width=True):
                    st.session_state["pending_question"] = q

        st.divider()
        st.caption("由 DeepSeek + LangChain + FAISS 提供技术支持")

    return page, selected_module
