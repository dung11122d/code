from __future__ import annotations

from schemas import Segment


def build_timeline(segments: list[Segment]) -> list[dict]:
    return [
        {
            "id": s.id,
            "start_ms": int(s.start_time * 1000),
            "end_ms": int(s.end_time * 1000),
            "duration_ms": int(s.duration * 1000),
            "tts_path": s.tts_path,
            "vi_text": s.vi_text,
        }
        for s in segments
    ]
