from __future__ import annotations

import subprocess
from pathlib import Path


def mux_audio_to_video(
    input_video: Path,
    input_audio: Path,
    output_video: Path,
    ffmpeg_bin: str = "ffmpeg",
) -> None:
    output_video.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(input_video),
        "-i",
        str(input_audio),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(output_video),
    ]
    subprocess.run(cmd, check=True)
