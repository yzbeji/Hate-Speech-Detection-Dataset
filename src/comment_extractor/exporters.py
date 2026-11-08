from __future__ import annotations

import json
from pathlib import Path

from comment_extractor.models import CommentRecord


class JsonlExporter:
    """Appends records to a JSONL file, skipping comments already in it (several posts share one file)."""

    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.seen_comment_ids: set[str] = set()
        if output_path.exists():
            self._load_existing_ids()

    def _load_existing_ids(self) -> None:
        with self.output_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cid = str(payload.get("comment_id") or "").strip()
                if cid:
                    self.seen_comment_ids.add(cid)

    def write(self, records: list[CommentRecord]) -> int:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        with self.output_path.open("a", encoding="utf-8", newline="\n") as handle:
            for record in records:
                if record.comment_id in self.seen_comment_ids:
                    continue
                payload = record.model_dump(mode="json")
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
                self.seen_comment_ids.add(record.comment_id)
                written += 1
        return written
