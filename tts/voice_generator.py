from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import librosa
import soundfile as sf
from pydub import AudioSegment
from pydub.effects import normalize
from TTS.api import TTS

from schemas import Segment


class VoiceGenerator:
    def __init__(
        self,
        backend: str,
        model: str,
        logger: logging.Logger,
        piper_exe: str | None = None,
        piper_model_path: str | None = None,
    ) -> None:
        self.backend = backend.lower()
        self.model = model
        self.logger = logger
        self.piper_exe = piper_exe
        self.piper_model_path = piper_model_path
        self.coqui = None
        if self.backend == "coqui":
            self.coqui = TTS(model_name=model, progress_bar=False, gpu=False)

    def synthesize_segments(self, segments: list[Segment], out_dir: Path) -> list[Segment]:
        out_dir.mkdir(parents=True, exist_ok=True)
        for seg in segments:
            if seg.tts_path and Path(seg.tts_path).exists():
                continue
            wav_path = out_dir / f"seg_{seg.id:04d}.wav"
            self.synthesize_text(seg.vi_text, wav_path)
            self._post_process(wav_path, seg.duration)
            seg.tts_path = str(wav_path)
        return segments

    def synthesize_text(self, text: str, wav_path: Path) -> None:
        if self.backend == "coqui":
            assert self.coqui is not None
            self.coqui.tts_to_file(text=text, file_path=str(wav_path))
            return

        if self.backend == "piper":
            if not self.piper_exe or not self.piper_model_path:
                raise ValueError("piper_exe and piper_model_path are required for Piper backend")
            cmd = [
                self.piper_exe,
                "--model",
                self.piper_model_path,
                "--output_file",
                str(wav_path),
            ]
            subprocess.run(cmd, input=text.encode("utf-8"), check=True)
            return

        raise ValueError(f"Unsupported TTS backend: {self.backend}")

    def _post_process(self, wav_path: Path, target_duration: float) -> None:
        y, sr = librosa.load(str(wav_path), sr=None)
        current = len(y) / sr if sr else 0.0
        if current > max(target_duration, 0.1):
            rate = min(1.35, max(1.0, current / max(target_duration, 0.1)))
            y = librosa.effects.time_stretch(y, rate=rate)
            sf.write(str(wav_path), y, sr)

        audio = AudioSegment.from_file(wav_path)
        audio = normalize(audio) - 2
        audio = audio.fade_in(20).fade_out(35)
        audio.export(wav_path, format="wav")
