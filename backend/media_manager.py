"""媒体文件管理：首页轮播图、工作人员档案。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from backend.config import ASSETS_DIR

HOSPITAL_IMAGES_DIR = ASSETS_DIR / "hospital_images"
STAFF_DIR = ASSETS_DIR / "staff"
STAFF_DATA_FILE = ASSETS_DIR / "staff_data.json"
HOME_IMAGES_FILE = ASSETS_DIR / "home_images.json"

HOSPITAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
STAFF_DIR.mkdir(parents=True, exist_ok=True)


# ── Hospital images ──────────────────────────────────────────────────

def _load_home_images() -> list[dict]:
    if HOME_IMAGES_FILE.exists():
        try:
            return json.loads(HOME_IMAGES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_home_images(data: list[dict]) -> None:
    HOME_IMAGES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_hospital_image(uploaded_file, caption: str = "") -> dict:
    suffix = Path(uploaded_file.name).suffix.lower()
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{suffix}"
    (HOSPITAL_IMAGES_DIR / filename).write_bytes(uploaded_file.getvalue())
    images = _load_home_images()
    entry = {
        "filename": filename,
        "caption": caption,
        "uploaded_at": datetime.now().isoformat(),
    }
    images.append(entry)
    _save_home_images(images)
    return entry


def list_hospital_images() -> list[dict]:
    return [
        {**img, "path": str(HOSPITAL_IMAGES_DIR / img["filename"])}
        for img in _load_home_images()
        if (HOSPITAL_IMAGES_DIR / img["filename"]).exists()
    ]


def delete_hospital_image(filename: str) -> None:
    path = HOSPITAL_IMAGES_DIR / filename
    if path.exists():
        path.unlink()
    _save_home_images([img for img in _load_home_images() if img["filename"] != filename])


def update_image_caption(filename: str, caption: str) -> None:
    images = _load_home_images()
    for img in images:
        if img["filename"] == filename:
            img["caption"] = caption
            break
    _save_home_images(images)


def move_image(filename: str, direction: int) -> None:
    """direction: -1 上移，+1 下移"""
    images = _load_home_images()
    idx = next((i for i, img in enumerate(images) if img["filename"] == filename), -1)
    new_idx = idx + direction
    if idx >= 0 and 0 <= new_idx < len(images):
        images[idx], images[new_idx] = images[new_idx], images[idx]
        _save_home_images(images)


# ── Staff management ─────────────────────────────────────────────────

def _load_staff() -> list[dict]:
    if STAFF_DATA_FILE.exists():
        try:
            return json.loads(STAFF_DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_staff(data: list[dict]) -> None:
    STAFF_DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_staff_member(
    name: str, title: str, department: str, intro: str, photo_file=None
) -> dict:
    staff_id = uuid.uuid4().hex[:8]
    photo_filename = None
    if photo_file is not None:
        suffix = Path(photo_file.name).suffix.lower()
        photo_filename = f"staff_{staff_id}{suffix}"
        (STAFF_DIR / photo_filename).write_bytes(photo_file.getvalue())

    entry = {
        "id": staff_id,
        "name": name,
        "title": title,
        "department": department,
        "intro": intro,
        "photo": photo_filename,
        "created_at": datetime.now().isoformat(),
    }
    staff = _load_staff()
    staff.append(entry)
    _save_staff(staff)
    return entry


def list_staff() -> list[dict]:
    result = []
    for s in _load_staff():
        photo_path = None
        if s.get("photo"):
            p = STAFF_DIR / s["photo"]
            if p.exists():
                photo_path = str(p)
        result.append({**s, "photo_path": photo_path})
    return result


def update_staff_member(
    staff_id: str,
    name: str,
    title: str,
    department: str,
    intro: str,
    photo_file=None,
) -> None:
    staff = _load_staff()
    for s in staff:
        if s["id"] == staff_id:
            s.update({"name": name, "title": title, "department": department, "intro": intro})
            if photo_file is not None:
                if s.get("photo"):
                    old = STAFF_DIR / s["photo"]
                    if old.exists():
                        old.unlink()
                suffix = Path(photo_file.name).suffix.lower()
                photo_filename = f"staff_{staff_id}{suffix}"
                (STAFF_DIR / photo_filename).write_bytes(photo_file.getvalue())
                s["photo"] = photo_filename
            break
    _save_staff(staff)


def delete_staff_member(staff_id: str) -> None:
    staff = _load_staff()
    for s in staff:
        if s["id"] == staff_id and s.get("photo"):
            photo_path = STAFF_DIR / s["photo"]
            if photo_path.exists():
                photo_path.unlink()
    _save_staff([s for s in staff if s["id"] != staff_id])
