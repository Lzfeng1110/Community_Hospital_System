"""居民智能问答页面（流式输出 + 引用来源 + 聊天历史）。"""

from __future__ import annotations

import json
import time

import streamlit as st

from backend.config import MODULES
from backend.rag_engine import chat_stream
from backend.log_manager import log_query

_SOURCE_TOKEN_START = "__SOURCES__"
_SOURCE_TOKEN_END = "__SOURCES_END__"


def _parse_stream(generator) -> tuple[str, list[str]]:
    """收集流式输出，分离正文与 sources 标记。"""
    full_text = ""
    sources: list[str] = []
    buffer = ""

    for chunk in generator:
        buffer += chunk
        if _SOURCE_TOKEN_START in buffer:
            idx = buffer.index(_SOURCE_TOKEN_START)
            full_text += buffer[:idx]
            remainder = buffer[idx:]
            if _SOURCE_TOKEN_END in remainder:
                raw = remainder[
                    len(_SOURCE_TOKEN_START): remainder.index(_SOURCE_TOKEN_END)
                ]
                try:
                    sources = json.loads(raw)
                except Exception:
                    sources = []
                break
        else:
            # 保留可能是标记前缀的部分，其余写入正文
            safe_len = max(0, len(buffer) - len(_SOURCE_TOKEN_START))
            full_text += buffer[:safe_len]
            buffer = buffer[safe_len:]

    return full_text, sources


def render_chat_page(module: str) -> None:
    module_name = MODULES.get(module, "全部知识库")
    st.markdown(f"## 💬 智能问答 · {module_name}")
    st.caption("请用自然语言描述您的问题，系统将从知识库中为您检索答案。")

    # 初始化会话状态
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_module" not in st.session_state:
        st.session_state.chat_module = module

    # 切换模块时清空历史
    if st.session_state.chat_module != module:
        st.session_state.messages = []
        st.session_state.chat_module = module

    # 清空对话按钮
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🗑️ 清空", help="清空当前对话历史"):
            st.session_state.messages = []
            st.rerun()

    # 渲染历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🏥"):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📎 参考来源", expanded=False):
                    for src in msg["sources"]:
                        st.caption(f"• {src}")

    # 处理快捷问题点击
    pending = st.session_state.pop("pending_question", None)

    # 输入框
    user_input = st.chat_input("请输入您的问题，例如：医保报销比例是多少？")
    question = pending or user_input

    if not question:
        if not st.session_state.messages:
            st.info("👋 您好！我是大观街道社区卫生服务中心智能助手，请选择左侧类别后输入您的问题。")
        return

    # 显示用户消息
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(question)

    # 构建历史（排除最后一条刚加入的 user 消息）
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
    ]

    # 流式输出
    with st.chat_message("assistant", avatar="🏥"):
        placeholder = st.empty()
        full_answer = ""
        sources: list[str] = []
        buffer = ""
        start = time.time()

        try:
            generator = chat_stream(question, module, history)
            for chunk in generator:
                if _SOURCE_TOKEN_START in (buffer + chunk):
                    combined = buffer + chunk
                    idx = combined.index(_SOURCE_TOKEN_START)
                    full_answer += combined[:idx]
                    remainder = combined[idx:]
                    if _SOURCE_TOKEN_END in remainder:
                        raw = remainder[
                            len(_SOURCE_TOKEN_START): remainder.index(_SOURCE_TOKEN_END)
                        ]
                        try:
                            sources = json.loads(raw)
                        except Exception:
                            sources = []
                    buffer = ""
                    break
                else:
                    safe_len = max(0, len(buffer + chunk) - len(_SOURCE_TOKEN_START))
                    safe_part = (buffer + chunk)[:safe_len]
                    full_answer += safe_part
                    buffer = (buffer + chunk)[safe_len:]
                    placeholder.markdown(full_answer + "▌")

            placeholder.markdown(full_answer)

        except Exception as e:
            full_answer = f"⚠️ 系统暂时无法回答，请稍后重试。（{e}）"
            placeholder.markdown(full_answer)

        # 显示来源
        if sources:
            with st.expander("📎 参考来源", expanded=False):
                for src in sources:
                    st.caption(f"• {src}")

    duration_ms = int((time.time() - start) * 1000)

    # 保存到会话历史
    st.session_state.messages.append({
        "role": "assistant",
        "content": full_answer,
        "sources": sources,
    })

    # 异步记录日志
    try:
        log_query(
            module=module,
            question=question,
            answer=full_answer,
            sources=sources,
            duration_ms=duration_ms,
        )
    except Exception:
        pass
