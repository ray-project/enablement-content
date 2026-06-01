#!/usr/bin/env python3
"""Copy mapped videos + metadata into each module's local videos/ folder."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
COURSES_ROOT = ROOT / "courses"
THINKIFIC_ROOT = ROOT / "videos" / "Thinkific Course Videos"
TRANSCRIPTS_ROOT = ROOT / "videos" / "transcripts"
FRAMES_ROOT = ROOT / "videos" / "frame_information"


def collect_video_paths(video_lessons: dict) -> list[str]:
    paths: list[str] = []
    for value in video_lessons.values():
        if isinstance(value, str):
            paths.append(value)
        elif isinstance(value, list):
            paths.extend(value)
    return paths


def metadata_dir(root: Path, thinkific_rel: str) -> Path:
    return root / Path(thinkific_rel).with_suffix("")


def copy_metadata(src_dir: Path, dest_dir: Path) -> int:
    if not src_dir.is_dir():
        return 0
    copied = 0
    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in src_dir.iterdir():
        dest = dest_dir / item.name
        if item.is_dir():
            copied += copy_tree(item, dest)
        elif not dest.exists() or item.stat().st_mtime > dest.stat().st_mtime:
            shutil.copy2(item, dest)
            copied += 1
    return copied


def copy_tree(src: Path, dest: Path) -> int:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return sum(1 for _ in dest.rglob("*") if _.is_file())


def materialize_video(thinkific_rel: str, module_videos_dir: Path) -> str:
    """Copy mp4/mp3 + metadata; return local path for module.yaml."""
    src_mp4 = THINKIFIC_ROOT / thinkific_rel
    if not src_mp4.is_file():
        raise FileNotFoundError(f"Missing video: {src_mp4}")

    filename = src_mp4.name
    local_rel = f"videos/{filename}"
    dest_mp4 = module_videos_dir / filename

    module_videos_dir.mkdir(parents=True, exist_ok=True)
    if not dest_mp4.exists() or src_mp4.stat().st_mtime > dest_mp4.stat().st_mtime:
        shutil.copy2(src_mp4, dest_mp4)

    src_mp3 = src_mp4.with_suffix(".mp3")
    dest_mp3 = dest_mp4.with_suffix(".mp3")
    if src_mp3.is_file() and (
        not dest_mp3.exists() or src_mp3.stat().st_mtime > dest_mp3.stat().st_mtime
    ):
        shutil.copy2(src_mp3, dest_mp3)

    stem = src_mp4.stem
    meta_dir = module_videos_dir / stem
    copy_metadata(metadata_dir(TRANSCRIPTS_ROOT, thinkific_rel), meta_dir / "transcripts")
    copy_metadata(metadata_dir(FRAMES_ROOT, thinkific_rel), meta_dir / "frame_information")

    return local_rel


def rewrite_video_lessons(
    video_lessons: dict[str, str | list[str] | None],
    module_videos_dir: Path,
    path_map: dict[str, str],
) -> dict[str, str | list[str] | None]:
    updated: dict[str, str | list[str] | None] = {}
    for lesson_id, value in video_lessons.items():
        if value is None:
            updated[lesson_id] = None
        elif isinstance(value, str):
            if value not in path_map:
                path_map[value] = materialize_video(value, module_videos_dir)
            updated[lesson_id] = path_map[value]
        elif isinstance(value, list):
            local_paths = []
            for thinkific_rel in value:
                if thinkific_rel not in path_map:
                    path_map[thinkific_rel] = materialize_video(thinkific_rel, module_videos_dir)
                local_paths.append(path_map[thinkific_rel])
            updated[lesson_id] = local_paths
    return updated


def is_thinkific_path(path: str) -> bool:
    return not path.startswith("videos/")


def process_module(yaml_path: Path) -> tuple[int, int]:
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    mod_key = next(iter(data))
    mod = data[mod_key]
    video_lessons = mod.get("videoLessons")
    if not video_lessons:
        return 0, 0

    thinkific_paths = [p for p in collect_video_paths(video_lessons) if is_thinkific_path(p)]
    if not thinkific_paths:
        return 0, 0

    module_videos_dir = yaml_path.parent / "videos"
    path_map: dict[str, str] = {}
    mod["videoLessons"] = rewrite_video_lessons(video_lessons, module_videos_dir, path_map)

    with open(yaml_path, "w") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
        )

    return len(thinkific_paths), len(path_map)


def main() -> None:
    if not THINKIFIC_ROOT.is_dir():
        raise SystemExit(f"Thinkific videos not found: {THINKIFIC_ROOT}")

    total_videos = 0
    total_modules = 0

    for yaml_path in sorted(COURSES_ROOT.rglob("module.yaml")):
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        mod = data[next(iter(data))]
        if not mod.get("videoLessons"):
            continue

        count, unique = process_module(yaml_path)
        if count:
            rel = yaml_path.relative_to(COURSES_ROOT).parent
            print(f"{rel}: {unique} video(s)")
            total_videos += count
            total_modules += 1

    print(f"\nMaterialized {total_videos} video references across {total_modules} modules.")


if __name__ == "__main__":
    main()
