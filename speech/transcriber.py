from __future__ import annotations

import logging
from typing import Iterable

from faster_whisper import WhisperModel

from schemas import Segment


class ChineseTranscriber:
    def __init__(
        self,
        model_name: str,
        device: str = "auto",
        compute_type: str = "int8",
        logger: logging.Logger | None = None,
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.model = WhisperModel(model_name, device=device, compute_type=compute_type)

    def transcribe(self, audio_path: str, language: str = "zh") -> list[Segment]:
        raw_segments, _ = self.model.transcribe(
            audio_path,
            language=language,
            vad_filter=True,
            word_timestamps=False,
        )
        segments = self._to_segments(raw_segments)
        self.logger.info("ASR complete: %d segments", len(segments))
        return segments

    def _to_segments(self, raw_segments: Iterable) -> list[Segment]:
        results: list[Segment] = []
        seg_id = 1
        for s in raw_segments:
            text = s.text.strip()
            if not text:
                continue
            results.append(
                Segment(
                    id=seg_id,
                    start_time=max(0.0, float(s.start)),
                    end_time=max(float(s.end), float(s.start) + 0.01),
                    original_text=text,
                )
            )
            seg_id += 1
        return results
