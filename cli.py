from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="China->Vietnamese video dubbing pipeline")
    p.add_argument("--config", type=Path, default=Path("config/config.example.yaml"))
    p.add_argument("--resume", action="store_true", help="Resume from saved progress")
    p.add_argument("--skip-translation", action="store_true")
    p.add_argument("--skip-tts", action="store_true")
    p.add_argument("--export-srt", action="store_true")
    return p
