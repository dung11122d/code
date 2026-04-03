from __future__ import annotations

import json
from pathlib import Path

from cli import build_parser
from config import AppConfig, load_config
from dubbing.audio_mixer import mix_voice_with_background
from dubbing.timeline_builder import build_timeline
from dubbing.video_muxer import mux_audio_to_video
from schemas import PipelinePaths, Segment
from speech.transcriber import ChineseTranscriber
from translator.chatgpt_browser import ChatGPTBrowserTranslator
from tts.voice_generator import VoiceGenerator
from utils.file_utils import read_json, video_output_dir, write_json
from utils.logger import setup_logger
from video.audio_extractor import extract_audio, extract_background_track


def init_paths(config: AppConfig, out_dir: Path) -> PipelinePaths:
    return PipelinePaths(
        out_dir=out_dir,
        extracted_audio=out_dir / "extracted_audio.wav",
        transcript_json=out_dir / "transcript.json",
        translated_json=out_dir / "translated_segments.json",
        raw_chat_dir=out_dir / "raw_chat",
        tts_dir=out_dir / "generated_tts",
        final_voice=out_dir / "final_voice_track.wav",
        final_audio=out_dir / "final_audio.wav",
        final_video=out_dir / "final_video_vi.mp4",
        progress_json=out_dir / "progress.json",
        subtitles_srt=out_dir / "translated_vi.srt",
    )


def load_segments(path: Path) -> list[Segment]:
    data = read_json(path, default=[])
    return [Segment(**item) for item in data]


def save_segments(path: Path, segments: list[Segment]) -> None:
    write_json(path, [s.to_dict() for s in segments])


def write_progress(path: Path, stage: str, meta: dict | None = None) -> None:
    payload = {"stage": stage, "meta": meta or {}}
    write_json(path, payload)


def export_srt(path: Path, segments: list[Segment]) -> None:
    lines: list[str] = []
    for i, s in enumerate(segments, 1):
        st = _to_srt_time(s.start_time)
        et = _to_srt_time(s.end_time)
        lines.extend([str(i), f"{st} --> {et}", s.vi_text or s.original_text, ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _to_srt_time(seconds: float) -> str:
    ms = int((seconds % 1) * 1000)
    total = int(seconds)
    s = total % 60
    m = (total // 60) % 60
    h = total // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def should_overwrite(path: Path) -> bool:
    if not path.exists():
        return True
    ans = input(f"{path} already exists. Overwrite? [y/N]: ").strip().lower()
    return ans == "y"


def run() -> None:
    args = build_parser().parse_args()
    cfg = load_config(args.config)

    out_dir = video_output_dir(cfg.output_root, cfg.input_video)
    paths = init_paths(cfg, out_dir)
    logger = setup_logger(out_dir / "pipeline.log")
    logger.info("Output dir: %s", out_dir)

    if not paths.extracted_audio.exists():
        logger.info("Extracting audio...")
        extract_audio(cfg.input_video, paths.extracted_audio, cfg.ffmpeg_path)
    write_progress(paths.progress_json, "audio_extracted")

    if not paths.transcript_json.exists():
        logger.info("Running ASR...")
        transcriber = ChineseTranscriber(
            model_name=cfg.asr_model,
            device=cfg.asr_device,
            compute_type=cfg.asr_compute_type,
            logger=logger,
        )
        segments = transcriber.transcribe(str(paths.extracted_audio), language=cfg.language)
        save_segments(paths.transcript_json, segments)
    else:
        segments = load_segments(paths.transcript_json)
    write_progress(paths.progress_json, "asr_done", {"segments": len(segments)})

    translated = load_segments(paths.translated_json) if paths.translated_json.exists() else segments

    if not args.skip_translation:
        translator = ChatGPTBrowserTranslator(
            chromedriver_path=cfg.chromedriver_path,
            profile_dir=cfg.chrome_profile_dir,
            selectors=cfg.selectors,
            chatgpt_url=cfg.chatgpt_url,
            max_retries=cfg.translation_retry,
            delay_sec=cfg.translation_delay_sec,
            logger=logger,
            headless=cfg.headless,
            chrome_binary=cfg.chrome_binary,
        )
        try:
            translator.open_and_wait_login()
            translated = translator.translate_segments(translated)
            save_segments(paths.translated_json, translated)
            write_progress(paths.progress_json, "translation_done")
        finally:
            translator.close()

    if args.skip_translation and not paths.translated_json.exists():
        raise FileNotFoundError("--skip-translation used but translated_segments.json not found")
    if args.skip_translation:
        translated = load_segments(paths.translated_json)

    if not args.skip_tts:
        tts = VoiceGenerator(
            backend=cfg.tts_backend,
            model=cfg.tts_model,
            logger=logger,
            piper_exe=cfg.piper_exe,
            piper_model_path=cfg.piper_model_path,
        )
        translated = tts.synthesize_segments(translated, paths.tts_dir)
        save_segments(paths.translated_json, translated)
        write_progress(paths.progress_json, "tts_done")

    timeline = build_timeline(translated)

    bg_track = out_dir / "background_track.wav"
    if cfg.mix_mode != "voice_only":
        extract_background_track(cfg.input_video, bg_track, cfg.ffmpeg_path, cfg.keep_background_db)

    last_end_ms = int(max((s.end_time for s in translated), default=0.0) * 1000) + 300
    mix_voice_with_background(
        timeline=timeline,
        total_duration_ms=last_end_ms,
        final_voice_path=paths.final_voice,
        final_mix_path=paths.final_audio,
        background_wav=bg_track if bg_track.exists() else None,
        keep_background_db=0.0,
        ducking_db=cfg.ducking_db,
        mode=cfg.mix_mode,
    )
    write_progress(paths.progress_json, "audio_mixed")

    if should_overwrite(paths.final_video):
        mux_audio_to_video(cfg.input_video, paths.final_audio, paths.final_video, cfg.ffmpeg_path)
    write_progress(paths.progress_json, "video_muxed", {"video": str(paths.final_video)})

    if args.export_srt:
        export_srt(paths.subtitles_srt, translated)

    print(json.dumps({"status": "ok", "output_dir": str(out_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
