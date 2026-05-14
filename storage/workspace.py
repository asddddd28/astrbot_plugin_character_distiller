from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from astrbot.core.star.star_tools import StarTools


class DistillerWorkspace:
    def __init__(self, plugin_name: str):
        self.root = StarTools.get_data_dir(plugin_name)

    def ensure_layout(self) -> None:
        for child in ("works", "logs", "review_queue"):
            (self.root / child).mkdir(parents=True, exist_ok=True)

    def works_dir(self) -> Path:
        path = self.root / "works"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def next_work_id(self) -> str:
        existing = []
        for path in self.works_dir().glob("work_*"):
            try:
                existing.append(int(path.name.split("_", 1)[1]))
            except (IndexError, ValueError):
                continue
        return f"work_{(max(existing, default=0) + 1):03d}"

    def work_dir(self, work_id: str) -> Path:
        return self.works_dir() / work_id

    def require_work_dir(self, work_id: str) -> Path:
        path = self.work_dir(work_id)
        if not path.exists():
            raise FileNotFoundError(f"作品不存在：{work_id}")
        return path

    def ensure_work_layout(self, work_id: str) -> Path:
        base = self.work_dir(work_id)
        for child in (
            "raw",
            "index",
            "db",
            "rag_export/kb_chunks",
            "rag_export/memorix_import",
            "rag_export/angel_memory_import",
            "distilled",
            "exports",
            "eval",
        ):
            (base / child).mkdir(parents=True, exist_ok=True)
        return base

    @staticmethod
    def read_json(path: Path, default: Any = None) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
        path.write_text(text + ("\n" if text else ""), encoding="utf-8")

    @staticmethod
    def read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows

    @staticmethod
    def copy_source(source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
