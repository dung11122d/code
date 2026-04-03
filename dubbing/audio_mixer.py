from __future__ import annotations

import math
from pathlib import Path

from pydub import AudioSegment


def _safe_headroom(audio: AudioSegment, target_peak_dbfs: float = -1.0) -> AudioSegment:
    if audio.max_dBFS == float("-inf"):
        return audio
    diff = target_peak_dbfs - audio.max_dBFS
    return audio.apply_gain(diff) if diff < 0 else audio


def mix_voice_with_background(
    timeline: list[dict],
    total_duration_ms: int,
    final_voice_path: Path,
    final_mix_path: Path,
    background_wav: Path | None = None,
    keep_background_db: float = -18.0,
    ducking_db: float = -10.0,
    mode: str = "voice_plus_bg",
) -> None:
    voice_canvas = AudioSegment.silent(duration=total_duration_ms, frame_rate=24000)

    for item in timeline:
        clip = AudioSegment.from_file(item["tts_path"])
        seg_duration = max(item["duration_ms"], 1)
        if len(clip) < seg_duration:
            clip = clip + AudioSegment.silent(duration=(seg_duration - len(clip)))
        voice_canvas = voice_canvas.overlay(clip, position=item["start_ms"])

    voice_canvas = _safe_headroom(voice_canvas)
    final_voice_path.parent.mkdir(parents=True, exist_ok=True)
    voice_canvas.export(final_voice_path, format="wav")

    if mode == "voice_only" or not background_wav:
        voice_canvas.export(final_mix_path, format="wav")
        return

    bg = AudioSegment.from_file(background_wav).apply_gain(keep_background_db)
    if len(bg) < total_duration_ms:
        bg = bg + AudioSegment.silent(duration=(total_duration_ms - len(bg)))
    bg = bg[:total_duration_ms]

    for item in timeline:
        start = item["start_ms"]
        end = min(total_duration_ms, item["end_ms"])
        part = bg[start:end].apply_gain(ducking_db)
        bg = bg[:start] + part + bg[end:]

    mixed = _safe_headroom(bg.overlay(voice_canvas))
    if math.isinf(mixed.max_dBFS):
        mixed = voice_canvas
    mixed.export(final_mix_path, format="wav")
