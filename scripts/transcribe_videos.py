#!/usr/bin/env python3
"""Transcribe course videos with ElevenLabs Speech-to-Text (Scribe v2).

Uses the batch STT API with word-level timestamps:
https://elevenlabs.io/docs/api-reference/speech-to-text/convert

Outputs per video (mirroring the source path under videos/transcripts/):
  transcript.md   — clean readable transcript + timestamped segments
  transcript.json — full API payload, word timings, and course-mapping hints

Examples:
  # Preview what would run (no API calls)
  python courses/transcribe_videos.py --dry-run

  # Transcribe one video
  python courses/transcribe_videos.py --video "LLM_course/Module 1/1 - intro serve llm.mp4"

  # Transcribe all videos missing transcripts (idempotent)
  python courses/transcribe_videos.py

  # Re-transcribe even if outputs already exist
  python courses/transcribe_videos.py --video "..." --force

Requires ELEVENLABS_API_KEY (or XI_API_KEY) in the environment or a .env file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
VIDEOS_ROOT = ROOT / "videos" / "Thinkific Course Videos"
TRANSCRIPTS_ROOT = ROOT / "videos" / "transcripts"
MAPPING_PATH = ROOT / "courses" / "video_mapping.json"
LEGACY_PREFIX = "Ray 101 Course/old"
DEFAULT_MODEL = "scribe_v2"


@dataclass
class VideoJob:
    video_path: Path
    rel_video: str  # relative to VIDEOS_ROOT
    output_dir: Path
    mapping_hint: dict[str, Any] | None
    already_done: bool


def load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass


def get_api_key() -> str | None:
    return os.getenv("ELEVENLABS_API_KEY") or os.getenv("XI_API_KEY")


def load_video_mapping_index() -> dict[str, dict[str, Any]]:
    if not MAPPING_PATH.exists():
        return {}
    with open(MAPPING_PATH) as f:
        data = json.load(f)

    index: dict[str, dict[str, Any]] = {}
    for module in data.get("course_mappings", []):
        for mapping in module.get("mappings", []):
            video = mapping.get("video")
            if not video:
                continue
            index[video] = {
                "course_path": module.get("course_path"),
                "module_dir": module.get("module_dir"),
                "module_title": module.get("module_title"),
                "lesson_id": mapping.get("lesson_id"),
                "lesson_title": mapping.get("lesson_title"),
                "part": mapping.get("part"),
            }
    return index


def is_legacy(rel_video: str) -> bool:
    return rel_video.startswith(LEGACY_PREFIX)


def discover_videos(*, include_legacy: bool = False) -> list[Path]:
    if not VIDEOS_ROOT.exists():
        return []
    videos = sorted(VIDEOS_ROOT.rglob("*.mp4"))
    if include_legacy:
        return videos
    return [v for v in videos if not is_legacy(str(v.relative_to(VIDEOS_ROOT)))]


def resolve_video_arg(video_arg: str) -> Path:
    candidate = Path(video_arg)
    if candidate.is_file():
        return candidate.resolve()

    rel = video_arg.removeprefix("videos/").removeprefix("Thinkific Course Videos/")
    if not rel.endswith(".mp4"):
        rel += ".mp4"
    path = VIDEOS_ROOT / rel
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {video_arg} (resolved to {path})")
    return path


def output_dir_for(video_path: Path) -> Path:
    rel = video_path.relative_to(VIDEOS_ROOT)
    return TRANSCRIPTS_ROOT / rel.with_suffix("")


def is_transcribed(output_dir: Path) -> bool:
    return (output_dir / "transcript.json").exists() and (output_dir / "transcript.md").exists()


def build_jobs(
    videos: list[Path], mapping_index: dict[str, dict[str, Any]]
) -> list[VideoJob]:
    jobs: list[VideoJob] = []
    for video_path in videos:
        rel_video = str(video_path.relative_to(VIDEOS_ROOT))
        out_dir = output_dir_for(video_path)
        jobs.append(
            VideoJob(
                video_path=video_path,
                rel_video=rel_video,
                output_dir=out_dir,
                mapping_hint=mapping_index.get(rel_video),
                already_done=is_transcribed(out_dir),
            )
        )
    return jobs


def to_plain(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_plain(v) for v in obj]
    if hasattr(obj, "model_dump"):
        return to_plain(obj.model_dump())
    if hasattr(obj, "__dict__"):
        return to_plain(vars(obj))
    return str(obj)


def normalize_transcription(raw: Any) -> dict[str, Any]:
    data = to_plain(raw)
    if isinstance(data, dict) and "transcripts" in data:
        # Multichannel — use first channel for now
        transcripts = data.get("transcripts") or []
        if transcripts:
            merged = dict(transcripts[0])
            merged["transcription_id"] = data.get("transcription_id")
            merged["audio_duration_secs"] = data.get("audio_duration_secs")
            return merged
    if isinstance(data, dict):
        return data
    return {"text": str(data), "words": []}


def format_timestamp(seconds: float | None) -> str:
    if seconds is None:
        return "??:??:??"
    total = max(0, int(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def build_segments(words: list[dict[str, Any]], interval_seconds: float = 45.0) -> list[dict[str, Any]]:
    if not words:
        return []

    segments: list[dict[str, Any]] = []
    bucket: list[dict[str, Any]] = []
    bucket_start: float | None = None

    for word in words:
        if word.get("type") == "audio_event":
            continue
        start = word.get("start")
        if start is None:
            continue
        if bucket_start is None:
            bucket_start = start
        bucket.append(word)
        if start - bucket_start >= interval_seconds:
            segments.append(
                {
                    "start": bucket_start,
                    "end": word.get("end"),
                    "text": " ".join((w.get("text") or "").strip() for w in bucket if (w.get("text") or "").strip()),
                }
            )
            bucket = []
            bucket_start = None

    if bucket:
        segments.append(
            {
                "start": bucket_start,
                "end": bucket[-1].get("end"),
                "text": " ".join((w.get("text") or "").strip() for w in bucket if (w.get("text") or "").strip()),
            }
        )
    return segments


def render_markdown(job: VideoJob, payload: dict[str, Any], segments: list[dict[str, Any]]) -> str:
    lines = [
        f"# Transcript: {job.video_path.name}",
        "",
        f"- **Source video:** `{job.rel_video}`",
        f"- **Transcribed at:** {payload.get('transcribed_at', '')}",
        f"- **Model:** {payload.get('model_id', DEFAULT_MODEL)}",
        f"- **Language:** {payload.get('language_code', 'unknown')} "
        f"(confidence: {payload.get('language_probability', 'n/a')})",
    ]
    if payload.get("audio_duration_secs") is not None:
        lines.append(f"- **Duration:** {payload['audio_duration_secs']:.1f}s")
    if job.mapping_hint:
        hint = job.mapping_hint
        part = f" (part {hint['part']})" if hint.get("part") else ""
        lines.append(
            f"- **Mapped lesson:** `{hint.get('course_path')}` / "
            f"`{hint.get('module_dir')}` / `{hint.get('lesson_id')}`{part} — "
            f"{hint.get('lesson_title', '')}"
        )
    lines.extend(["", "## Full transcript", "", payload.get("text", "").strip(), ""])
    if segments:
        lines.extend(["## Timestamped segments", ""])
        for seg in segments:
            start = format_timestamp(seg.get("start"))
            end = format_timestamp(seg.get("end"))
            lines.append(f"### [{start} – {end}]")
            lines.append("")
            lines.append(seg.get("text", "").strip())
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def transcribe_with_elevenlabs(video_path: Path, *, language_code: str | None) -> dict[str, Any]:
    from elevenlabs.client import ElevenLabs

    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "Missing API key. Set ELEVENLABS_API_KEY or XI_API_KEY in the environment or .env file."
        )

    client = ElevenLabs(api_key=api_key)
    kwargs: dict[str, Any] = {
        "model_id": DEFAULT_MODEL,
        "timestamps_granularity": "word",
        "tag_audio_events": False,
        "diarize": False,
    }
    if language_code:
        kwargs["language_code"] = language_code

    with open(video_path, "rb") as f:
        raw = client.speech_to_text.convert(file=f, **kwargs)

    return normalize_transcription(raw)


def write_outputs(job: VideoJob, transcription: dict[str, Any], *, model_id: str) -> None:
    words = transcription.get("words") or []
    segments = build_segments(words)

    payload = {
        "source_video": job.rel_video,
        "source_video_absolute": str(job.video_path),
        "transcribed_at": datetime.now(timezone.utc).isoformat(),
        "model_id": model_id,
        "mapping_hint": job.mapping_hint,
        "language_code": transcription.get("language_code"),
        "language_probability": transcription.get("language_probability"),
        "audio_duration_secs": transcription.get("audio_duration_secs"),
        "transcription_id": transcription.get("transcription_id"),
        "text": transcription.get("text", ""),
        "words": words,
        "segments": segments,
    }

    job.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = job.output_dir / "transcript.json"
    md_path = job.output_dir / "transcript.md"

    with open(json_path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with open(md_path, "w") as f:
        f.write(render_markdown(job, payload, segments))


def print_dry_run(jobs: list[VideoJob], *, force: bool) -> None:
    pending = [j for j in jobs if force or not j.already_done]
    done = [j for j in jobs if j.already_done and not force]

    print(f"Videos root:      {VIDEOS_ROOT}")
    print(f"Transcripts root: {TRANSCRIPTS_ROOT}")
    print(f"Mapping index:    {MAPPING_PATH} ({'found' if MAPPING_PATH.exists() else 'missing'})")
    print(f"API key present:  {'yes' if get_api_key() else 'no'}")
    print()
    print(f"Total videos:     {len(jobs)}")
    print(f"Already done:     {len(done)}")
    print(f"Would transcribe: {len(pending)}")
    print()

    if done:
        print("Skip (already transcribed):")
        for job in done[:10]:
            print(f"  - {job.rel_video}")
        if len(done) > 10:
            print(f"  ... and {len(done) - 10} more")
        print()

    if pending:
        print("Would transcribe:")
        for job in pending[:20]:
            mapped = "mapped" if job.mapping_hint else "unmapped"
            print(f"  - {job.rel_video} [{mapped}]")
            print(f"    -> {job.output_dir.relative_to(ROOT)}")
        if len(pending) > 20:
            print(f"  ... and {len(pending) - 20} more")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--video",
        help="Transcribe a single video (path, or relative to Thinkific Course Videos/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be transcribed without calling the API",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-transcribe even if transcript.json already exists",
    )
    parser.add_argument(
        "--include-legacy",
        action="store_true",
        help=f"Include videos under {LEGACY_PREFIX}/",
    )
    parser.add_argument(
        "--language",
        default="eng",
        help="ISO-639 language code (default: eng). Pass 'auto' to let ElevenLabs detect.",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv_if_available()
    args = parse_args()
    mapping_index = load_video_mapping_index()

    if args.video:
        videos = [resolve_video_arg(args.video)]
    else:
        videos = discover_videos(include_legacy=args.include_legacy)

    jobs = build_jobs(videos, mapping_index)
    if not jobs:
        print(f"No videos found under {VIDEOS_ROOT}", file=sys.stderr)
        return 1

    if args.dry_run:
        print_dry_run(jobs, force=args.force)
        return 0

    if not get_api_key():
        print(
            "Error: ELEVENLABS_API_KEY (or XI_API_KEY) is not set.\n"
            "Use --dry-run to inspect the queue without an API key.",
            file=sys.stderr,
        )
        return 1

    language_code = None if args.language == "auto" else args.language
    processed = 0
    skipped = 0
    failed = 0

    for job in jobs:
        if job.already_done and not args.force:
            skipped += 1
            print(f"skip  {job.rel_video}")
            continue
        try:
            print(f"start {job.rel_video}")
            transcription = transcribe_with_elevenlabs(job.video_path, language_code=language_code)
            write_outputs(job, transcription, model_id=DEFAULT_MODEL)
            processed += 1
            print(f"done  {job.output_dir.relative_to(ROOT)}")
        except Exception as exc:
            failed += 1
            print(f"fail  {job.rel_video}: {exc}", file=sys.stderr)

    print()
    print(f"Processed: {processed}  Skipped: {skipped}  Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
