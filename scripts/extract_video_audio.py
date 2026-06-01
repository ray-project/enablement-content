#!/usr/bin/env python3
"""Extract MP3 audio tracks from course videos, saved next to each source file.

Outputs sit alongside the original MP4 under videos/Thinkific Course Videos/:
  00 Intro.mp4  →  00 Intro.mp3

Examples:
  # Preview queue
  python courses/extract_video_audio.py --dry-run

  # Extract one video
  python courses/extract_video_audio.py --video "Ray 101 Course/04_Tune/00 Intro.mp4"

  # Extract all missing MP3s (idempotent)
  python courses/extract_video_audio.py

  # Re-extract even if MP3 already exists
  python courses/extract_video_audio.py --force

Requires ffmpeg on PATH with libmp3lame support.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parent.parent
VIDEOS_ROOT = ROOT / "videos" / "Thinkific Course Videos"
LEGACY_PREFIX = "Ray 101 Course/old"
DEFAULT_BITRATE = "128k"


@dataclass
class AudioJob:
    video_path: Path
    rel_video: str
    audio_path: Path
    already_done: bool


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


def audio_path_for(video_path: Path) -> Path:
    return video_path.with_suffix(".mp3")


def is_extracted(audio_path: Path, *, video_path: Path) -> bool:
    if not audio_path.is_file() or audio_path.stat().st_size == 0:
        return False
    return audio_path.stat().st_mtime >= video_path.stat().st_mtime


def build_jobs(videos: list[Path]) -> list[AudioJob]:
    jobs: list[AudioJob] = []
    for video_path in videos:
        rel_video = str(video_path.relative_to(VIDEOS_ROOT))
        out_path = audio_path_for(video_path)
        jobs.append(
            AudioJob(
                video_path=video_path,
                rel_video=rel_video,
                audio_path=out_path,
                already_done=is_extracted(out_path, video_path=video_path),
            )
        )
    return jobs


def has_audio_stream(video_path: Path) -> bool:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=codec_type",
        "-of",
        "csv=p=0",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return "audio" in result.stdout


def extract_audio(video_path: Path, audio_path: Path, *, bitrate: str) -> None:
    if not has_audio_stream(video_path):
        raise RuntimeError("Video has no audio stream")

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "libmp3lame",
        "-b:a",
        bitrate,
        "-ar",
        "44100",
        "-ac",
        "2",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"ffmpeg exited {result.returncode}")
    if not audio_path.is_file() or audio_path.stat().st_size == 0:
        raise RuntimeError("ffmpeg produced an empty MP3")


def print_dry_run(jobs: list[AudioJob], *, force: bool) -> None:
    pending = [j for j in jobs if force or not j.already_done]
    done = [j for j in jobs if j.already_done and not force]

    print(f"Videos root:   {VIDEOS_ROOT}")
    print(f"ffmpeg:        {which('ffmpeg') or 'NOT FOUND'}")
    print(f"ffprobe:       {which('ffprobe') or 'NOT FOUND'}")
    print()
    print(f"Total videos:  {len(jobs)}")
    print(f"Already done:  {len(done)}")
    print(f"Would extract: {len(pending)}")
    print()

    if done:
        print("Skip (MP3 already exists):")
        for job in done[:10]:
            print(f"  - {job.rel_video}")
        if len(done) > 10:
            print(f"  ... and {len(done) - 10} more")
        print()

    if pending:
        print("Would extract:")
        for job in pending[:20]:
            print(f"  - {job.rel_video}")
            print(f"    -> {job.audio_path.name}")
        if len(pending) > 20:
            print(f"  ... and {len(pending) - 20} more")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--video",
        help="Extract audio from a single video (path, or relative to Thinkific Course Videos/)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show queue without extracting")
    parser.add_argument("--force", action="store_true", help="Re-extract even if MP3 already exists")
    parser.add_argument(
        "--include-legacy",
        action="store_true",
        help=f"Include videos under {LEGACY_PREFIX}/",
    )
    parser.add_argument(
        "--bitrate",
        default=DEFAULT_BITRATE,
        help=f"MP3 bitrate (default: {DEFAULT_BITRATE})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not which("ffmpeg") or not which("ffprobe"):
        print("Error: ffmpeg and ffprobe must be on PATH.", file=sys.stderr)
        return 1

    if args.video:
        videos = [resolve_video_arg(args.video)]
    else:
        videos = discover_videos(include_legacy=args.include_legacy)

    jobs = build_jobs(videos)
    if not jobs:
        print(f"No videos found under {VIDEOS_ROOT}", file=sys.stderr)
        return 1

    if args.dry_run:
        print_dry_run(jobs, force=args.force)
        return 0

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
            extract_audio(job.video_path, job.audio_path, bitrate=args.bitrate)
            processed += 1
            size_mb = job.audio_path.stat().st_size / (1024 * 1024)
            print(f"done  {job.audio_path.name} ({size_mb:.1f} MB)")
        except Exception as exc:
            failed += 1
            print(f"fail  {job.rel_video}: {exc}", file=sys.stderr)

    print()
    print(f"Processed: {processed}  Skipped: {skipped}  Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
