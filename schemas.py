from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class Segment:
    id: int
    start_time: float
    end_time: float
    original_text: str
    vi_text: str = ""
    tts_path: str = ""

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class PipelinePaths:
    out_dir: Path
    extracted_audio: Path
    transcript_json: Path
    translated_json: Path
    raw_chat_dir: Path
    tts_dir: Path
    final_voice: Path
    final_audio: Path
    final_video: Path
    progress_json: Path
    subtitles_srt: Path
