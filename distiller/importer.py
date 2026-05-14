from __future__ import annotations

from pathlib import Path

from .utils import normalize_text, read_text_auto, sha256_file, utc_now
from ..storage.workspace import DistillerWorkspace


class TextImporter:
    def __init__(self, workspace: DistillerWorkspace):
        self.workspace = workspace

    def import_text(self, title: str, source_path: Path) -> dict:
        source_path = source_path.expanduser()
        if not source_path.exists():
            raise FileNotFoundError(f"文件不存在：{source_path}")
        if source_path.suffix.lower() not in {".txt", ".md"}:
            raise ValueError("当前 MVP 仅支持 .txt 和 .md")

        work_id = self.workspace.next_work_id()
        base = self.workspace.ensure_work_layout(work_id)
        original_path = base / "raw" / f"original{source_path.suffix.lower()}"
        normalized_path = base / "raw" / "normalized.txt"

        self.workspace.copy_source(source_path, original_path)
        raw, source_encoding = read_text_auto(original_path)
        normalized = normalize_text(raw)
        normalized_path.write_text(normalized, encoding="utf-8")

        meta = {
            "work_id": work_id,
            "title": title,
            "source_type": "text",
            "language": "zh",
            "original_path": str(original_path.relative_to(base)),
            "normalized_path": str(normalized_path.relative_to(base)),
            "source_hash": sha256_file(original_path),
            "source_encoding": source_encoding,
            "created_at": utc_now(),
        }
        self.workspace.write_json(base / "raw" / "source_meta.json", meta)
        return meta
