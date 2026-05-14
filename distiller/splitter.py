from __future__ import annotations

from .utils import CHAPTER_RE, QUOTE_RE, detect_phase, short


class TextSplitter:
    def split(self, work_id: str, title: str, text: str) -> dict[str, list[dict]]:
        chapters = self._split_chapters(work_id, text)
        total = len(chapters)
        paragraphs: list[dict] = []
        scenes: list[dict] = []
        utterances: list[dict] = []

        for idx, chapter in enumerate(chapters):
            phase = detect_phase(idx, total)
            chapter["phase"] = phase
            chapter_paragraphs = self._paragraphs(chapter["text"])
            para_ids = []
            for p_idx, para in enumerate(chapter_paragraphs, start=1):
                pid = f"{chapter['chapter_id']}_p{p_idx:04d}"
                para_ids.append(pid)
                paragraphs.append(
                    {
                        "paragraph_id": pid,
                        "work_id": work_id,
                        "chapter_id": chapter["chapter_id"],
                        "phase": phase,
                        "index": p_idx,
                        "text": para,
                    }
                )
                for q_idx, quote in enumerate(QUOTE_RE.findall(para), start=1):
                    utterances.append(
                        {
                            "utterance_id": f"{pid}_u{q_idx:02d}",
                            "work_id": work_id,
                            "chapter_id": chapter["chapter_id"],
                            "scene_id": "",
                            "speaker": "unknown",
                            "listener": "unknown",
                            "phase": phase,
                            "text": quote,
                            "confidence": 0.0,
                        }
                    )

            for s_idx, batch in enumerate(self._scene_batches(para_ids), start=1):
                scenes.append(
                    {
                        "scene_id": f"{chapter['chapter_id']}_s{s_idx:03d}",
                        "work_id": work_id,
                        "chapter_id": chapter["chapter_id"],
                        "phase": phase,
                        "characters": [],
                        "event_type": [],
                        "emotion_tags": [],
                        "paragraph_ids": batch,
                        "summary": "",
                    }
                )

            chapter["summary"] = short(chapter["text"], 120)
            chapter["text"] = None

        scene_by_para = {
            pid: scene["scene_id"] for scene in scenes for pid in scene["paragraph_ids"]
        }
        for utt in utterances:
            pid = utt["utterance_id"].rsplit("_u", 1)[0]
            utt["scene_id"] = scene_by_para.get(pid, "")

        return {
            "chapters": chapters,
            "paragraphs": paragraphs,
            "scenes": scenes,
            "utterances": utterances,
        }

    def _split_chapters(self, work_id: str, text: str) -> list[dict]:
        lines = text.splitlines()
        starts: list[tuple[int, str]] = []
        for i, line in enumerate(lines):
            if CHAPTER_RE.match(line.strip()):
                starts.append((i, line.strip()))

        if not starts:
            return [
                {
                    "chapter_id": f"{work_id}_ch001",
                    "work_id": work_id,
                    "chapter_index": 1,
                    "title": "全文",
                    "char_start": 0,
                    "char_end": len(text),
                    "text": text,
                }
            ]

        chapters = []
        char_offsets = []
        cursor = 0
        for line in lines:
            char_offsets.append(cursor)
            cursor += len(line) + 1

        for idx, (line_no, chapter_title) in enumerate(starts, start=1):
            next_line = starts[idx][0] if idx < len(starts) else len(lines)
            body = "\n".join(lines[line_no:next_line]).strip()
            char_start = char_offsets[line_no]
            char_end = char_offsets[next_line - 1] + len(lines[next_line - 1]) if next_line > line_no else char_start
            chapters.append(
                {
                    "chapter_id": f"{work_id}_ch{idx:03d}",
                    "work_id": work_id,
                    "chapter_index": idx,
                    "title": chapter_title,
                    "char_start": char_start,
                    "char_end": char_end,
                    "text": body,
                }
            )
        return chapters

    @staticmethod
    def _paragraphs(text: str) -> list[str]:
        parts = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(parts) <= 1:
            parts = [p.strip() for p in text.splitlines() if p.strip()]
        return parts

    @staticmethod
    def _scene_batches(ids: list[str], size: int = 8) -> list[list[str]]:
        return [ids[i : i + size] for i in range(0, len(ids), size)] or [[]]
