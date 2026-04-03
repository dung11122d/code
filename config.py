from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class AppConfig:
    input_video: Path
    output_root: Path
    ffmpeg_path: str
    chromedriver_path: Path
    chrome_binary: str | None
    chrome_profile_dir: Path
    chatgpt_url: str
    headless: bool
    debug_browser: bool
    asr_model: str
    asr_device: str
    asr_compute_type: str
    language: str
    tts_backend: str
    tts_model: str
    piper_exe: str | None
    piper_model_path: str | None
    mix_mode: str
    keep_background_db: float
    ducking_db: float
    translation_batch_size: int
    translation_retry: int
    translation_delay_sec: float
    selectors: dict[str, Any]


def load_config(path: Path) -> AppConfig:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    return AppConfig(
        input_video=Path(cfg["input_video"]),
        output_root=Path(cfg["output_root"]),
        ffmpeg_path=cfg.get("ffmpeg_path", "ffmpeg"),
        chromedriver_path=Path(cfg["chrome"]["chromedriver_path"]),
        chrome_binary=cfg["chrome"].get("binary"),
        chrome_profile_dir=Path(cfg["chrome"]["profile_dir"]),
        chatgpt_url=cfg["chatgpt"]["url"],
        headless=bool(cfg["chrome"].get("headless", False)),
        debug_browser=bool(cfg["chrome"].get("debug_browser", True)),
        asr_model=cfg["asr"]["model"],
        asr_device=cfg["asr"].get("device", "auto"),
        asr_compute_type=cfg["asr"].get("compute_type", "int8"),
        language=cfg["asr"].get("language", "zh"),
        tts_backend=cfg["tts"]["backend"],
        tts_model=cfg["tts"].get("model", ""),
        piper_exe=cfg["tts"].get("piper_exe"),
        piper_model_path=cfg["tts"].get("piper_model_path"),
        mix_mode=cfg["audio"]["mix_mode"],
        keep_background_db=float(cfg["audio"].get("background_gain_db", -18.0)),
        ducking_db=float(cfg["audio"].get("ducking_db", -10.0)),
        translation_batch_size=int(cfg["translation"].get("batch_size", 5)),
        translation_retry=int(cfg["translation"].get("max_retries", 3)),
        translation_delay_sec=float(cfg["translation"].get("delay_sec", 1.2)),
        selectors=cfg["chatgpt"]["selectors"],
    )
