from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class CheckpointState:
    source_url: str
    output_path: str
    total_written: int
    updated_at: str


def write_checkpoint(path: Path, source_url: str, output_path: str, total_written: int) -> None:
    payload = CheckpointState(
        source_url=source_url,
        output_path=output_path,
        total_written=total_written,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    path.write_text(json.dumps(payload.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
