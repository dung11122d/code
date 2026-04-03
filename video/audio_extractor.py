from __future__ import annotations

import subprocess
from pathlib import Path


def extract_audio(video_path: Path, out_wav: Path, ffmpeg_bin: str = "ffmpeg") -> None:
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(out_wav),
    ]
    subprocess.run(cmd, check=True)


def extract_background_track(
    video_path: Path,
    out_wav: Path,
    ffmpeg_bin: str = "ffmpeg",
    gain_db: float = -18.0,
) -> None:
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-af",
        f"volume={gain_db}dB",
        str(out_wav),
    ]
    subprocess.run(cmd, check=True)
