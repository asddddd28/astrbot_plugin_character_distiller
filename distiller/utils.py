from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone


CHAPTER_RE = re.compile(
    r"^\s*(第[一二三四五六七八九十百千万零〇两\d]+[章节卷回幕].*|chapter\s+\d+.*|\d+[\.、]\s+.+)\s*$",
    re.IGNORECASE,
)
QUOTE_RE = re.compile(r"[“\"'「『‘]([^“”\"'「」『』‘’]{1,240})[”\"'」』’]")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def read_text_auto(path) -> tuple[str, str]:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n"


def detect_phase(index: int, total: int) -> str:
    if total <= 1:
        return "middle"
    ratio = index / max(total - 1, 1)
    if ratio < 0.34:
        return "early"
    if ratio < 0.68:
        return "middle"
    return "late"


def short(text: str, limit: int = 160) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


def safe_filename(value: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value).strip(" ._")
    return safe or "unnamed"
