#!/usr/bin/env python3
"""Extract opening frames from course videos and analyze on-screen notebook content.

Course walkthrough videos typically show a Jupyter notebook in Anyscale/VS Code.
Grabbing an early frame (~10th, skipping black intro frames) and running vision
analysis reveals the notebook title, filename tab, and visible section header —
useful for validating or correcting video-to-lesson mappings.

Outputs per video (mirroring the source path under videos/frame_information/):
  frame.png       — selected snapshot (first non-black candidate frame)
  frame_info.json — structured analysis + mapping hints
  frame_info.md   — human-readable summary

Examples:
  # Preview queue (no ffmpeg analysis calls beyond listing)
  python courses/extract_frame_info.py --dry-run

  # Extract + analyze one video
  python courses/extract_frame_info.py --video "Ray 101 Course/04_Tune/00 Intro.mp4"

  # Extract frames only (no vision API — useful without OPENAI_API_KEY)
  python courses/extract_frame_info.py --extract-only

  # Process all unprocessed videos (idempotent)
  python courses/extract_frame_info.py

  # Re-process even if outputs exist
  python courses/extract_frame_info.py --force

  # Summary report comparing frame analysis to video_mapping.json
  python courses/extract_frame_info.py --report

Requires ffmpeg on PATH. Vision analysis uses OPENAI_API_KEY (gpt-4o-mini) unless
--extract-only is set.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
VIDEOS_ROOT = ROOT / "videos" / "Thinkific Course Videos"
FRAMES_ROOT = ROOT / "videos" / "frame_information"
MAPPING_PATH = ROOT / "courses" / "video_mapping.json"
LEGACY_PREFIX = "Ray 101 Course/old"
DEFAULT_MODEL = "gpt-4o-mini"

# 0-indexed frame numbers to try (skip black intro frames)
CANDIDATE_FRAMES = [10, 30, 60, 90, 150, 300]
MIN_BRIGHTNESS = 18.0  # 0–255 grayscale mean; below this = likely black/blank

VISION_PROMPT = """You are analyzing a screenshot from a Ray/Anyscale course video walkthrough.
The presenter is typically showing a Jupyter notebook inside Anyscale (VS Code web UI).

Extract what is visible on screen. Focus on text that helps map this video to a specific
course lesson or notebook section.

Return JSON with exactly these keys:
{
  "notebook_filename": "e.g. 03_Intro_Ray_Tune.ipynb or null if not visible",
  "notebook_title": "main H1 title in the notebook, or null",
  "visible_section": "current section header shown (e.g. '1. Loading and visualizing data'), or null",
  "visible_headers": ["list of markdown headers visible on screen"],
  "open_notebook_tabs": ["other .ipynb tab names visible"],
  "roadmap_parts": ["numbered parts from any roadmap/outline callout box, if visible"],
  "interface": "brief description: Anyscale workspace, slides, terminal, browser, etc.",
  "content_summary": "1-2 sentences describing what the viewer sees",
  "likely_start_of_notebook": true/false — whether this looks like the beginning of a notebook walkthrough
}

Be precise with notebook filenames and section numbers. If text is unreadable, use null."""


@dataclass
class VideoJob:
    video_path: Path
    rel_video: str
    output_dir: Path
    mapping_hint: dict[str, Any] | None
    already_done: bool


def load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass


def get_openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY")


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
    return FRAMES_ROOT / rel.with_suffix("")


def is_processed(output_dir: Path, *, require_analysis: bool) -> bool:
    has_frame = (output_dir / "frame.png").exists()
    has_json = (output_dir / "frame_info.json").exists()
    if not has_frame or not has_json:
        return False
    if require_analysis:
        with open(output_dir / "frame_info.json") as f:
            data = json.load(f)
        return data.get("screen_analysis") is not None
    return True


def build_jobs(
    videos: list[Path],
    mapping_index: dict[str, dict[str, Any]],
    *,
    require_analysis: bool,
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
                already_done=is_processed(out_dir, require_analysis=require_analysis),
            )
        )
    return jobs


def run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )


def frame_brightness(path: Path) -> float:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for non-black frame selection. "
            "Install with: pip install -r requirements-frame-info.txt"
        ) from exc

    with Image.open(path) as img:
        gray = img.convert("L")
        pixels = gray.get_flattened_data()
        return sum(pixels) / len(pixels)


def extract_candidate_frame(video_path: Path, frame_index: int, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vf",
        f"select=eq(n\\,{frame_index})",
        "-vframes",
        "1",
        "-update",
        "1",
        str(dest),
    ]
    result = run_ffmpeg(cmd)
    return result.returncode == 0 and dest.exists() and dest.stat().st_size > 0


def pillow_available() -> bool:
    try:
        import PIL  # noqa: F401

        return True
    except ImportError:
        return False


def select_frame(video_path: Path, dest: Path) -> dict[str, Any]:
    """Try candidate frame indices; pick first non-black frame."""
    if not pillow_available():
        frame_index = CANDIDATE_FRAMES[0]
        if not extract_candidate_frame(video_path, frame_index, dest):
            raise RuntimeError("Could not extract frame from video")
        return {
            "frame_index": frame_index,
            "brightness": None,
            "candidate_frames_tried": [{"frame_index": frame_index, "note": "Pillow not installed"}],
            "fallback": "used default frame index (install Pillow for black-frame detection)",
        }

    attempts: list[dict[str, Any]] = []
    for frame_index in CANDIDATE_FRAMES:
        tmp = dest.with_suffix(f".try{frame_index}.png")
        if not extract_candidate_frame(video_path, frame_index, tmp):
            attempts.append({"frame_index": frame_index, "error": "ffmpeg failed"})
            continue

        brightness = frame_brightness(tmp)
        attempts.append({"frame_index": frame_index, "brightness": round(brightness, 2)})
        if brightness >= MIN_BRIGHTNESS:
            tmp.replace(dest)
            return {
                "frame_index": frame_index,
                "brightness": round(brightness, 2),
                "candidate_frames_tried": attempts,
            }

        tmp.unlink(missing_ok=True)

    # Fall back to the brightest candidate
    best_index = None
    best_brightness = -1.0
    for frame_index in CANDIDATE_FRAMES:
        tmp = dest.with_suffix(f".try{frame_index}.png")
        if extract_candidate_frame(video_path, frame_index, tmp):
            brightness = frame_brightness(tmp)
            if brightness > best_brightness:
                best_brightness = brightness
                best_index = frame_index
                tmp.replace(dest)
            else:
                tmp.unlink(missing_ok=True)

    if best_index is None:
        raise RuntimeError("Could not extract any frame from video")

    return {
        "frame_index": best_index,
        "brightness": round(best_brightness, 2),
        "candidate_frames_tried": attempts,
        "fallback": "used brightest candidate",
    }


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = value.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text)


def compute_alignment(
    screen_analysis: dict[str, Any], mapping_hint: dict[str, Any] | None
) -> dict[str, Any]:
    if not mapping_hint:
        return {"status": "unmapped", "notes": "No entry in video_mapping.json"}

    mapped_title = mapping_hint.get("lesson_title") or ""
    visible_section = screen_analysis.get("visible_section") or ""
    notebook_title = screen_analysis.get("notebook_title") or ""
    roadmap = screen_analysis.get("roadmap_parts") or []

    mapped_norm = normalize_text(mapped_title)
    section_norm = normalize_text(visible_section)
    title_norm = normalize_text(notebook_title)

    matches: list[str] = []
    if mapped_norm and section_norm and (mapped_norm in section_norm or section_norm in mapped_norm):
        matches.append("visible_section matches mapped lesson title")
    if mapped_norm and title_norm and (mapped_norm in title_norm or title_norm in mapped_norm):
        matches.append("notebook_title relates to mapped lesson title")

    # Check if visible section number aligns with lesson id (e.g. 01_lesson -> "1. ...")
    lesson_id = mapping_hint.get("lesson_id") or ""
    id_match = re.match(r"(\d+)_lesson", lesson_id)
    if id_match and visible_section:
        lesson_num = id_match.group(1).lstrip("0") or "0"
        if re.match(rf"^{lesson_num}\.", visible_section.strip()):
            matches.append(f"section number matches {lesson_id}")

    part = mapping_hint.get("part")
    scenario = None
    notes: list[str] = []

    if part:
        scenario = "A"
        notes.append(f"Video is part {part} of lesson {lesson_id} (one lesson split across videos)")
    elif len(roadmap) > 1 and screen_analysis.get("likely_start_of_notebook"):
        scenario = "B"
        notes.append(
            "Roadmap shows multiple parts at notebook start — one video may cover several lessons"
        )
    elif matches:
        scenario = "aligned"
        notes.append("On-screen content aligns with current mapping")
    else:
        scenario = "review"
        notes.append(
            "On-screen section/title does not obviously match mapped lesson — manual review suggested"
        )

    return {
        "status": "match" if matches else "mismatch",
        "likely_scenario": scenario,
        "match_signals": matches,
        "mapped_lesson_title": mapped_title,
        "visible_section": visible_section,
        "notebook_title": notebook_title,
        "notes": notes,
    }


def analyze_frame_with_openai(frame_path: Path, *, model: str) -> dict[str, Any]:
    from openai import OpenAI

    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Set it in .env or use --extract-only to skip vision analysis."
        )

    with open(frame_path, "rb") as f:
        image_b64 = base64.standard_b64encode(f.read()).decode("ascii")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}", "detail": "high"},
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=800,
    )

    content = response.choices[0].message.content or "{}"
    return json.loads(content)


def render_markdown(job: VideoJob, payload: dict[str, Any]) -> str:
    lines = [
        f"# Frame analysis: {job.video_path.name}",
        "",
        f"- **Source video:** `{job.rel_video}`",
        f"- **Analyzed at:** {payload.get('analyzed_at', '')}",
        f"- **Frame index:** {payload.get('frame_index')} "
        f"(brightness: {payload.get('brightness')})",
    ]
    if payload.get("vision_model"):
        lines.append(f"- **Vision model:** {payload['vision_model']}")

    if job.mapping_hint:
        hint = job.mapping_hint
        part = f" (part {hint['part']})" if hint.get("part") else ""
        lines.append(
            f"- **Mapped lesson:** `{hint.get('course_path')}` / "
            f"`{hint.get('module_dir')}` / `{hint.get('lesson_id')}`{part} — "
            f"{hint.get('lesson_title', '')}"
        )

    analysis = payload.get("screen_analysis") or {}
    if analysis:
        lines.extend(["", "## On-screen content", ""])
        if analysis.get("notebook_filename"):
            lines.append(f"- **Notebook file:** `{analysis['notebook_filename']}`")
        if analysis.get("notebook_title"):
            lines.append(f"- **Notebook title:** {analysis['notebook_title']}")
        if analysis.get("visible_section"):
            lines.append(f"- **Visible section:** {analysis['visible_section']}")
        if analysis.get("interface"):
            lines.append(f"- **Interface:** {analysis['interface']}")
        if analysis.get("content_summary"):
            lines.append(f"- **Summary:** {analysis['content_summary']}")
        if analysis.get("open_notebook_tabs"):
            lines.append(f"- **Open tabs:** {', '.join(analysis['open_notebook_tabs'])}")
        if analysis.get("roadmap_parts"):
            lines.append("- **Roadmap parts:**")
            for part in analysis["roadmap_parts"]:
                lines.append(f"  - {part}")
        if analysis.get("visible_headers"):
            lines.append("- **Visible headers:**")
            for header in analysis["visible_headers"]:
                lines.append(f"  - {header}")

    alignment = payload.get("alignment") or {}
    if alignment:
        lines.extend(["", "## Mapping alignment", ""])
        lines.append(f"- **Status:** {alignment.get('status', 'unknown')}")
        if alignment.get("likely_scenario"):
            lines.append(f"- **Likely scenario:** {alignment.get('likely_scenario')}")
        for note in alignment.get("notes") or []:
            lines.append(f"- {note}")
        for signal in alignment.get("match_signals") or []:
            lines.append(f"- ✓ {signal}")

    lines.append("")
    return "\n".join(lines)


def write_outputs(
    job: VideoJob,
    *,
    frame_meta: dict[str, Any],
    screen_analysis: dict[str, Any] | None,
    vision_model: str | None,
) -> None:
    alignment = compute_alignment(screen_analysis or {}, job.mapping_hint) if screen_analysis else None

    payload: dict[str, Any] = {
        "source_video": job.rel_video,
        "source_video_absolute": str(job.video_path),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "frame_index": frame_meta.get("frame_index"),
        "brightness": frame_meta.get("brightness"),
        "candidate_frames_tried": frame_meta.get("candidate_frames_tried"),
        "mapping_hint": job.mapping_hint,
        "vision_model": vision_model,
        "screen_analysis": screen_analysis,
        "alignment": alignment,
    }

    job.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = job.output_dir / "frame_info.json"
    md_path = job.output_dir / "frame_info.md"

    with open(json_path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with open(md_path, "w") as f:
        f.write(render_markdown(job, payload))


def process_job(job: VideoJob, *, extract_only: bool, model: str) -> None:
    frame_path = job.output_dir / "frame.png"
    frame_meta = select_frame(job.video_path, frame_path)

    screen_analysis = None
    vision_model = None
    if not extract_only:
        screen_analysis = analyze_frame_with_openai(frame_path, model=model)
        vision_model = model

    write_outputs(job, frame_meta=frame_meta, screen_analysis=screen_analysis, vision_model=vision_model)


def print_dry_run(jobs: list[VideoJob], *, force: bool, extract_only: bool) -> None:
    pending = [j for j in jobs if force or not j.already_done]
    done = [j for j in jobs if j.already_done and not force]

    print(f"Videos root:         {VIDEOS_ROOT}")
    print(f"Frame info root:     {FRAMES_ROOT}")
    print(f"Mapping index:       {MAPPING_PATH} ({'found' if MAPPING_PATH.exists() else 'missing'})")
    print(f"ffmpeg:              {shutil_which('ffmpeg') or 'NOT FOUND'}")
    print(f"OpenAI API key:      {'yes' if get_openai_api_key() else 'no'}")
    print(f"Mode:                {'extract-only' if extract_only else 'extract + vision analysis'}")
    print()
    print(f"Total videos:        {len(jobs)}")
    print(f"Already done:        {len(done)}")
    print(f"Would process:       {len(pending)}")
    print()

    if done:
        print("Skip (already processed):")
        for job in done[:10]:
            print(f"  - {job.rel_video}")
        if len(done) > 10:
            print(f"  ... and {len(done) - 10} more")
        print()

    if pending:
        print("Would process:")
        for job in pending[:20]:
            mapped = "mapped" if job.mapping_hint else "unmapped"
            print(f"  - {job.rel_video} [{mapped}]")
            print(f"    -> {job.output_dir.relative_to(ROOT)}")
        if len(pending) > 20:
            print(f"  ... and {len(pending) - 20} more")


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


def generate_report() -> int:
    if not FRAMES_ROOT.exists():
        print(f"No frame information found under {FRAMES_ROOT}", file=sys.stderr)
        return 1

    entries: list[dict[str, Any]] = []
    for json_path in sorted(FRAMES_ROOT.rglob("frame_info.json")):
        with open(json_path) as f:
            data = json.load(f)
        entries.append(data)

    if not entries:
        print("No frame_info.json files found.", file=sys.stderr)
        return 1

    aligned = [e for e in entries if (e.get("alignment") or {}).get("status") == "match"]
    mismatch = [e for e in entries if (e.get("alignment") or {}).get("status") == "mismatch"]
    unmapped = [e for e in entries if (e.get("alignment") or {}).get("status") == "unmapped"]
    no_analysis = [e for e in entries if not e.get("screen_analysis")]

    print(f"Frame information report ({len(entries)} videos)")
    print(f"  Aligned:     {len(aligned)}")
    print(f"  Mismatch:    {len(mismatch)}")
    print(f"  Unmapped:    {len(unmapped)}")
    print(f"  No analysis: {len(no_analysis)}")
    print()

    if mismatch:
        print("Review suggested (on-screen content vs mapping):")
        for entry in mismatch:
            alignment = entry.get("alignment") or {}
            analysis = entry.get("screen_analysis") or {}
            hint = entry.get("mapping_hint") or {}
            print(f"  - {entry.get('source_video')}")
            print(f"      mapped:   {hint.get('lesson_title', '—')}")
            print(f"      on-screen: {analysis.get('visible_section') or analysis.get('notebook_title') or '—'}")
            print(f"      scenario:  {alignment.get('likely_scenario', '—')}")
        print()

    scenario_b = [
        e
        for e in entries
        if (e.get("alignment") or {}).get("likely_scenario") == "B"
    ]
    if scenario_b:
        print(f"Likely multi-lesson videos (scenario B): {len(scenario_b)}")
        for entry in scenario_b[:15]:
            analysis = entry.get("screen_analysis") or {}
            parts = analysis.get("roadmap_parts") or []
            print(f"  - {entry.get('source_video')} ({len(parts)} roadmap parts)")
        if len(scenario_b) > 15:
            print(f"  ... and {len(scenario_b) - 15} more")
        print()

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--video",
        help="Process a single video (path, or relative to Thinkific Course Videos/)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show queue without processing")
    parser.add_argument("--force", action="store_true", help="Re-process even if outputs exist")
    parser.add_argument(
        "--include-legacy",
        action="store_true",
        help=f"Include videos under {LEGACY_PREFIX}/",
    )
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Extract frame.png only; skip OpenAI vision analysis",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI vision model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print alignment summary from existing frame_info.json files",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv_if_available()
    args = parse_args()

    if args.report:
        return generate_report()

    if not shutil_which("ffmpeg"):
        print("Error: ffmpeg not found on PATH.", file=sys.stderr)
        return 1

    extract_only = args.extract_only
    require_analysis = not extract_only
    mapping_index = load_video_mapping_index()

    if args.video:
        videos = [resolve_video_arg(args.video)]
    else:
        videos = discover_videos(include_legacy=args.include_legacy)

    jobs = build_jobs(videos, mapping_index, require_analysis=require_analysis)
    if not jobs:
        print(f"No videos found under {VIDEOS_ROOT}", file=sys.stderr)
        return 1

    if args.dry_run:
        print_dry_run(jobs, force=args.force, extract_only=extract_only)
        return 0

    if not extract_only and not get_openai_api_key():
        print(
            "Error: OPENAI_API_KEY is not set.\n"
            "Use --extract-only to grab frames without vision analysis,\n"
            "or --dry-run to inspect the queue.",
            file=sys.stderr,
        )
        return 1

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
            process_job(job, extract_only=extract_only, model=args.model)
            processed += 1
            rel_out = job.output_dir.relative_to(ROOT)
            print(f"done  {rel_out}")
        except Exception as exc:
            failed += 1
            print(f"fail  {job.rel_video}: {exc}", file=sys.stderr)

    print()
    print(f"Processed: {processed}  Skipped: {skipped}  Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
