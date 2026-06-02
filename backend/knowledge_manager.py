"""知识库文件管理：上传、删除、列表、状态查询。"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from backend.config import KNOWLEDGE_BASE_DIR, VECTOR_STORE_DIR, MODULES

META_FILE = KNOWLEDGE_BASE_DIR / "metadata.json"


def _load_meta() -> dict:
    if META_FILE.exists():
        return json.loads(META_FILE.read_text(encoding="utf-8"))
    return {}


def _save_meta(meta: dict) -> None:
    META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def save_uploaded_file(uploaded_file, module: str) -> Path:
    """将 Streamlit UploadedFile 保存到 knowledge_base/<module>/ 目录。"""
    target_dir = KNOWLEDGE_BASE_DIR / module
    target_dir.mkdir(exist_ok=True)
    dest = target_dir / uploaded_file.name
    dest.write_bytes(uploaded_file.getbuffer())

    meta = _load_meta()
    meta[str(dest)] = {
        "filename": uploaded_file.name,
        "module": module,
        "size": dest.stat().st_size,
        "uploaded_at": datetime.now().isoformat(),
    }
    _save_meta(meta)
    return dest


def delete_file(file_path: str) -> bool:
    p = Path(file_path)
    if p.exists():
        p.unlink()
    meta = _load_meta()
    meta.pop(file_path, None)
    _save_meta(meta)
    return True


def list_files(module: str = "all") -> list[dict]:
    meta = _load_meta()
    files = []
    for path, info in meta.items():
        if module == "all" or info.get("module") == module:
            files.append({
                "path": path,
                "filename": info.get("filename", Path(path).name),
                "module": info.get("module", "unknown"),
                "module_name": MODULES.get(info.get("module", ""), info.get("module", "")),
                "size_kb": round(info.get("size", 0) / 1024, 1),
                "uploaded_at": info.get("uploaded_at", ""),
            })
    return sorted(files, key=lambda x: x["uploaded_at"], reverse=True)


def get_files_by_module(module: str) -> list[Path]:
    """返回指定模块（或全部）的文件路径列表（仅存在的文件）。"""
    meta = _load_meta()
    paths = []
    for path_str, info in meta.items():
        if module == "all" or info.get("module") == module:
            p = Path(path_str)
            if p.exists():
                paths.append(p)
    return paths


def get_stats() -> dict:
    meta = _load_meta()
    total = len(meta)
    by_module: dict[str, int] = {}
    total_size = 0
    for info in meta.values():
        m = info.get("module", "unknown")
        by_module[m] = by_module.get(m, 0) + 1
        total_size += info.get("size", 0)
    return {
        "total_files": total,
        "by_module": by_module,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
    }


def clear_vector_store(module: str = "all") -> None:
    """删除向量库缓存，触发下次查询时重建。"""
    if module == "all":
        for p in VECTOR_STORE_DIR.iterdir():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    else:
        target = VECTOR_STORE_DIR / module
        if target.exists():
            shutil.rmtree(target)
