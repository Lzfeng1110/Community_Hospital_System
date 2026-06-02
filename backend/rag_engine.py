"""RAG 核心引擎：文档加载、向量化、检索、流式问答。"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Generator, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from backend.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    EMBEDDING_MODEL,
    VECTOR_STORE_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TOP_K,
    MAX_HISTORY_TURNS,
    MEDICAL_DISCLAIMER,
    MEDICAL_KEYWORDS,
    CENTER_INFO,
)
from backend.knowledge_manager import get_files_by_module

_embeddings: HuggingFaceEmbeddings | None = None
_vector_stores: dict[str, FAISS] = {}


def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def get_llm(streaming: bool = False) -> ChatOpenAI:
    return ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        streaming=streaming,
        temperature=0.3,
        max_tokens=2048,
    )


def _load_document(file_path: Path) -> list[Document]:
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".pdf":
            loader = PyPDFLoader(str(file_path))
        elif suffix in (".docx", ".doc"):
            loader = Docx2txtLoader(str(file_path))
        elif suffix == ".txt":
            loader = TextLoader(str(file_path), encoding="utf-8")
        else:
            return []
        docs = loader.load()
        for doc in docs:
            doc.metadata["source"] = file_path.name
            doc.metadata["file_path"] = str(file_path)
        return docs
    except Exception as e:
        print(f"[RAG] 加载文档失败 {file_path}: {e}")
        return []


def _build_vector_store(module: str) -> FAISS | None:
    files = get_files_by_module(module)
    if not files:
        return None

    all_docs: list[Document] = []
    for f in files:
        all_docs.extend(_load_document(f))

    if not all_docs:
        return None

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
    )
    chunks = splitter.split_documents(all_docs)

    store = FAISS.from_documents(chunks, get_embeddings())

    save_dir = VECTOR_STORE_DIR / module
    save_dir.mkdir(parents=True, exist_ok=True)
    store.save_local(str(save_dir))
    return store


def get_vector_store(module: str) -> FAISS | None:
    """获取向量库，优先加载缓存，缓存不存在则重建。"""
    global _vector_stores

    save_dir = VECTOR_STORE_DIR / module
    if module not in _vector_stores:
        if save_dir.exists() and any(save_dir.iterdir()):
            try:
                _vector_stores[module] = FAISS.load_local(
                    str(save_dir),
                    get_embeddings(),
                    allow_dangerous_deserialization=True,
                )
            except Exception:
                _vector_stores[module] = _build_vector_store(module)
        else:
            _vector_stores[module] = _build_vector_store(module)

    return _vector_stores.get(module)


def rebuild_vector_store(module: str = "all") -> str:
    """强制重建向量库（管理员操作）。"""
    global _vector_stores

    modules = list(["policy", "vaccine", "appointment", "notice"]) if module == "all" else [module]
    rebuilt = []

    for m in modules:
        _vector_stores.pop(m, None)
        store = _build_vector_store(m)
        if store:
            _vector_stores[m] = store
            rebuilt.append(m)

    if module == "all":
        _vector_stores.pop("all", None)

    if rebuilt:
        return f"成功重建知识库：{', '.join(rebuilt)}"
    return "未找到可用文档，请先上传文件。"


def _retrieve_docs(query: str, module: str) -> list[Document]:
    """从向量库检索相关文档片段。"""
    if module == "all":
        all_docs: list[Document] = []
        for m in ["policy", "vaccine", "appointment", "notice"]:
            store = get_vector_store(m)
            if store:
                results = store.similarity_search(query, k=TOP_K)
                all_docs.extend(results)
        return all_docs[:TOP_K * 2]
    else:
        store = get_vector_store(module)
        if store is None:
            return []
        return store.similarity_search(query, k=TOP_K)


def _contains_medical_sensitive(text: str) -> bool:
    return any(kw in text for kw in MEDICAL_KEYWORDS)


def _build_system_prompt(module: str) -> str:
    center = CENTER_INFO["name"]
    return f"""你是{center}的智能问答助手，专门帮助居民查询社区卫生服务相关信息。

当前服务模块：{module}

回答规则：
1. 仅根据提供的参考资料回答，不要编造信息。
2. 如果参考资料中没有相关内容，请明确告知"知识库中暂无该信息，建议拨打中心电话咨询"。
3. 回答简洁、友好、通俗易懂，适合普通居民阅读。
4. 引用具体政策条款时，请注明来源文件名。
5. 对于需要预约或现场办理的事项，请提醒居民具体操作步骤。

中心基本信息：
- 名称：{CENTER_INFO['name']}
- 地址：{CENTER_INFO['address']}
- 电话：{CENTER_INFO['phone']}
- 服务时间：{CENTER_INFO['hours']}
"""


def _format_context(docs: list[Document]) -> str:
    if not docs:
        return "（当前知识库暂无相关文档）"
    parts = []
    seen_sources = set()
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "未知文件")
        page = doc.metadata.get("page", "")
        page_str = f" 第{page+1}页" if page != "" else ""
        parts.append(f"【参考{i}】来源：{source}{page_str}\n{doc.page_content.strip()}")
        seen_sources.add(source)
    return "\n\n".join(parts)


def _extract_sources(docs: list[Document]) -> list[str]:
    seen = {}
    for doc in docs:
        source = doc.metadata.get("source", "未知文件")
        page = doc.metadata.get("page", "")
        key = f"{source} 第{page+1}页" if page != "" else source
        seen[key] = True
    return list(seen.keys())


def chat_stream(
    question: str,
    module: str,
    history: list[dict],
) -> Generator[str, None, None]:
    """流式问答生成器，yield 文本片段。最后 yield 特殊标记包含 sources。"""

    docs = _retrieve_docs(question, module)
    context = _format_context(docs)
    sources = _extract_sources(docs)

    system_content = _build_system_prompt(module)
    user_content = f"参考资料：\n{context}\n\n居民问题：{question}"

    messages: list = [SystemMessage(content=system_content)]
    for turn in history[-MAX_HISTORY_TURNS:]:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        elif turn["role"] == "assistant":
            messages.append(AIMessage(content=turn["content"]))
    messages.append(HumanMessage(content=user_content))

    llm = get_llm(streaming=True)
    full_answer = ""

    for chunk in llm.stream(messages):
        token = chunk.content
        if token:
            full_answer += token
            yield token

    needs_disclaimer = _contains_medical_sensitive(question) or _contains_medical_sensitive(full_answer)
    if needs_disclaimer:
        disclaimer = f"\n\n{MEDICAL_DISCLAIMER}"
        yield disclaimer
        full_answer += disclaimer

    import json as _json
    yield f"\n\n__SOURCES__{_json.dumps(sources, ensure_ascii=False)}__SOURCES_END__"


def chat_once(
    question: str,
    module: str,
    history: list[dict],
) -> tuple[str, list[str], int]:
    """非流式问答，返回 (answer, sources, duration_ms)。"""
    start = time.time()
    docs = _retrieve_docs(question, module)
    context = _format_context(docs)
    sources = _extract_sources(docs)

    system_content = _build_system_prompt(module)
    user_content = f"参考资料：\n{context}\n\n居民问题：{question}"

    messages: list = [SystemMessage(content=system_content)]
    for turn in history[-MAX_HISTORY_TURNS:]:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        elif turn["role"] == "assistant":
            messages.append(AIMessage(content=turn["content"]))
    messages.append(HumanMessage(content=user_content))

    llm = get_llm(streaming=False)
    response = llm.invoke(messages)
    answer = response.content

    if _contains_medical_sensitive(question) or _contains_medical_sensitive(answer):
        answer += f"\n\n{MEDICAL_DISCLAIMER}"

    duration_ms = int((time.time() - start) * 1000)
    return answer, sources, duration_ms


def invalidate_cache(module: str = "all") -> None:
    """清除内存中的向量库缓存，下次查询时重新加载。"""
    global _vector_stores
    if module == "all":
        _vector_stores.clear()
    else:
        _vector_stores.pop(module, None)
