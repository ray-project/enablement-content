#!/usr/bin/env python3
"""Sync video_mapping.json into module.yaml files as videoLessons (source of truth)."""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
COURSES_ROOT = ROOT / "courses"
MAPPING_PATH = COURSES_ROOT / "video_mapping.json"


def load_mapping_index() -> dict[tuple[str, str], list[dict]]:
    with open(MAPPING_PATH) as f:
        data = json.load(f)

    index: dict[tuple[str, str], list[dict]] = {}
    for module in data.get("course_mappings", []):
        key = (module["course_path"], module["module_dir"])
        index[key] = module.get("mappings", [])
    return index


def build_video_lessons(
    lesson_ids: list[str], mappings: list[dict]
) -> OrderedDict[str, str | list[str] | None]:
    by_lesson: dict[str, list[str]] = {lid: [] for lid in lesson_ids}
    orphan_videos: list[str] = []

    for entry in mappings:
        video = entry.get("video")
        lesson_id = entry.get("lesson_id")
        if not video:
            continue
        if lesson_id and lesson_id in by_lesson:
            by_lesson[lesson_id].append(video)
        else:
            orphan_videos.append(video)

    video_lessons: OrderedDict[str, str | list[str] | None] = OrderedDict()
    for lesson_id in lesson_ids:
        videos = by_lesson.get(lesson_id, [])
        if not videos:
            video_lessons[lesson_id] = None
        elif len(videos) == 1:
            video_lessons[lesson_id] = videos[0]
        else:
            video_lessons[lesson_id] = videos

    for video in orphan_videos:
        video_lessons[f"_unmapped_{len(video_lessons)}"] = video

    return video_lessons


def is_perfect_match(
    lesson_ids: list[str], video_lessons: OrderedDict[str, str | list[str] | None]
) -> bool:
    expected_keys = set(lesson_ids)
    actual_keys = {k for k in video_lessons if not k.startswith("_unmapped_")}
    if expected_keys != actual_keys:
        return False
    if any(k.startswith("_unmapped_") for k in video_lessons):
        return False

    for lesson_id in lesson_ids:
        value = video_lessons[lesson_id]
        if not isinstance(value, str):
            return False

    return True


def sync_module_yaml(path: Path, mappings: list[dict]) -> tuple[bool, bool]:
    with open(path) as f:
        data = yaml.safe_load(f)

    mod_key = next(iter(data))
    mod = data[mod_key]
    lesson_ids = sorted(mod.get("lessons", {}).keys())

    video_lessons = build_video_lessons(lesson_ids, mappings)
    perfect = is_perfect_match(lesson_ids, video_lessons)

    mod.pop("videoMatch", None)
    mod.pop("videoLessons", None)

    if not perfect:
        mod["videoMatch"] = False
    mod["videoLessons"] = dict(video_lessons)

    with open(path, "w") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
        )

    return perfect, not perfect


def main() -> None:
    index = load_mapping_index()
    perfect_count = 0
    mismatch_count = 0

    for (course_path, module_dir), mappings in sorted(index.items()):
        yaml_path = COURSES_ROOT / course_path / module_dir / "module.yaml"
        if not yaml_path.exists():
            print(f"SKIP missing yaml: {yaml_path}")
            continue

        perfect, flagged = sync_module_yaml(yaml_path, mappings)
        status = "OK" if perfect else "videoMatch: false"
        print(f"{status:18} {course_path}/{module_dir}")
        if perfect:
            perfect_count += 1
        if flagged:
            mismatch_count += 1

    print(f"\nUpdated {perfect_count + mismatch_count} modules "
          f"({perfect_count} perfect, {mismatch_count} flagged)")

    from materialize_module_videos import main as materialize

    print("\nMaterializing local videos/ folders...")
    materialize()


if __name__ == "__main__":
    main()
