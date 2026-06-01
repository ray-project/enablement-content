#!/usr/bin/env python3
"""Generate courses/video_mapping.json from videos/ and courses/ module.yaml files."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VIDEOS_ROOT = ROOT / "videos/Thinkific Course Videos"
COURSES_ROOT = ROOT / "courses"
OUT = COURSES_ROOT / "video_mapping.json"
LEGACY_PREFIX = "Ray 101 Course/old"


def natural_sort_key(path: Path) -> list:
    name = path.stem
    parts = re.split(r"(\d+)", name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def load_module_yaml(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path) as f:
        data = yaml.safe_load(f)
    for mod_id, mod in data.items():
        lessons = mod.get("lessons", {})
        return {
            "module_id": mod_id,
            "title": mod.get("title", ""),
            "lessons": [
                {"lesson_id": lid, "title": l.get("title", "")}
                for lid, l in sorted(lessons.items())
            ],
        }
    return None


def list_videos(rel_dir: str) -> list[str]:
    base = VIDEOS_ROOT / rel_dir
    if not base.exists():
        return []
    vids = sorted(base.rglob("*.mp4"), key=natural_sort_key)
    return [str(v.relative_to(VIDEOS_ROOT)) for v in vids]


def map_sequential(videos: list[str], lessons: list[dict]) -> list[dict]:
    mappings = []
    for i, video in enumerate(videos):
        if i < len(lessons):
            lesson = lessons[i]
            mappings.append(
                {
                    "video": video,
                    "lesson_id": lesson["lesson_id"],
                    "lesson_title": lesson["title"],
                }
            )
        else:
            mappings.append({"video": video, "lesson_id": None, "lesson_title": None})
    for j in range(len(videos), len(lessons)):
        lesson = lessons[j]
        mappings.append(
            {
                "video": None,
                "lesson_id": lesson["lesson_id"],
                "lesson_title": lesson["title"],
                "missing_video": True,
            }
        )
    return mappings


def mapping_entry(
    course_path: str,
    module_dir: str,
    video_source: str,
    *,
    video_subdir: str | None = None,
    videos: list[str] | None = None,
    notes: str | None = None,
    custom_mappings: list[dict] | None = None,
    legacy: bool = False,
) -> dict | None:
    if videos is None:
        if not video_subdir:
            return None
        videos = list_videos(video_subdir)
    if not videos and not custom_mappings:
        return None

    mod = load_module_yaml(COURSES_ROOT / course_path / module_dir / "module.yaml")
    lessons = mod["lessons"] if mod else []
    mappings = custom_mappings or map_sequential(videos, lessons)

    return {
        "course_path": course_path,
        "module_dir": module_dir,
        "module_title": mod["title"] if mod else module_dir,
        "video_source": video_source,
        "video_subdir": video_subdir,
        "video_count": len(videos),
        "lesson_count": len(lessons),
        "legacy": legacy,
        "notes": notes,
        "mappings": mappings,
    }


def module_mapping(
    course_path: str,
    module_dir: str,
    video_source: str,
    video_subdir: str,
    *,
    notes: str | None = None,
    custom_mappings: list[dict] | None = None,
) -> dict | None:
    return mapping_entry(
        course_path,
        module_dir,
        video_source,
        video_subdir=video_subdir,
        notes=notes,
        custom_mappings=custom_mappings,
    )


def anyscale_devs_mappings() -> list[dict]:
    """Flat Anyscale_for_Devs folder → Anyscale_Getting_Started modules 00–06."""
    devs = "Anyscale_for_Devs"
    course = "foundations/Anyscale_Getting_Started"
    pairs = [
        ("01_anyscale_intro.mp4", "00_Intro_to_Workspaces", "00_lesson", 1),
        ("02_intro_to_workspaces.mp4", "00_Intro_to_Workspaces", "00_lesson", 2),
        ("03_ Developing Applications with Anyscale.mp4", "01_dev_intro", "00_lesson", None),
        ("04 Compute Configs and Execution Environments in Anyscale.mp4", "02_compute_runtime", "00_lesson", None),
        ("05 Storage Options in the Anyscale Platform.mp4", "03_storage_options", "00_lesson", None),
        ("06 Debug and Monitor your Anyscale Application.mp4", "04_logging_metrics", "00_lesson", None),
        ("07 Introduction to Anyscale Jobs.mp4", "05_intro_jobs", "00_lesson", None),
        ("08 Introduction to Anyscale Services.mp4", "06_intro_services", "00_lesson", None),
    ]

    by_module: dict[str, list[dict]] = {}
    for filename, module_dir, lesson_id, part in pairs:
        rel = f"{devs}/{filename}"
        mod = load_module_yaml(COURSES_ROOT / course / module_dir / "module.yaml")
        lesson = next(l for l in mod["lessons"] if l["lesson_id"] == lesson_id)
        item = {
            "video": rel,
            "lesson_id": lesson_id,
            "lesson_title": lesson["title"],
        }
        if part is not None:
            item["part"] = part
        by_module.setdefault(module_dir, []).append(item)

    entries = []
    for module_dir, module_mappings in by_module.items():
        mod = load_module_yaml(COURSES_ROOT / course / module_dir / "module.yaml")
        notes = None
        if module_dir == "00_Intro_to_Workspaces":
            notes = "Videos 01–02 both map to 00_lesson (platform intro + workspaces intro)."
        entry = mapping_entry(
            course,
            module_dir,
            devs,
            video_subdir=devs,
            videos=[m["video"] for m in module_mappings],
            notes=notes,
            custom_mappings=module_mappings,
        )
        if entry:
            entries.append(entry)
    return entries


def ray_tune_mappings() -> dict | None:
    """Ray 101 Course/04_Tune → foundations/Ray_Tune/00_Tune."""
    subdir = "Ray 101 Course/04_Tune"
    videos = list_videos(subdir)
    if not videos:
        return None

    course = "foundations/Ray_Tune"
    mod_dir = "00_Tune"
    mod = load_module_yaml(COURSES_ROOT / course / mod_dir / "module.yaml")
    lessons = mod["lessons"]

    # 7 videos, 5 yaml lessons — HPT content spans videos 03–05 → lesson 03
    plan = [
        (0, "00_lesson"),
        (1, "01_lesson"),
        (2, "02_lesson"),
        (3, "03_lesson", 1),
        (4, "03_lesson", 2),
        (5, "03_lesson", 3),
        (6, "04_lesson"),
    ]
    custom = []
    for item in plan:
        idx, lesson_id = item[0], item[1]
        part = item[2] if len(item) > 2 else None
        lesson = next(l for l in lessons if l["lesson_id"] == lesson_id)
        mapping = {
            "video": videos[idx],
            "lesson_id": lesson_id,
            "lesson_title": lesson["title"],
        }
        if part is not None:
            mapping["part"] = part
        custom.append(mapping)

    return mapping_entry(
        course,
        mod_dir,
        "Ray 101 Course",
        video_subdir=subdir,
        videos=videos,
        notes=(
            "7 videos for 5 yaml lessons. Video 00 is chapter overview (five lectures in transcript). "
            "Videos 03–05 split yaml lesson 03 into three parts."
        ),
        custom_mappings=custom,
    )


def ray_train_and_data_mappings() -> dict | None:
    """Ray Train Videos/02 Integrating Ray Train with Ray Data → foundations/Ray_Train/02_train_and_data."""
    subdir = "Ray Train Videos/02 Integrating Ray Train with Ray Data"
    base = VIDEOS_ROOT / subdir
    if not base.exists():
        return None

    course = "foundations/Ray_Train"
    mod_dir = "02_train_and_data"
    mod = load_module_yaml(COURSES_ROOT / course / mod_dir / "module.yaml")
    if not mod:
        return None

    lesson_by_id = {l["lesson_id"]: l for l in mod["lessons"]}

    split_at_sec = 70.920
    full_backup = f"{subdir}/02-6 Configuring TorchTrainer and Launching Training (full).mp4"
    split_phrase = "So to save time, I'm just going to take a moment to run this"

    plan = [
        ("02-1 Introduction_.mp4", "00_lesson", None),
        ("02-2 Train Loop Using Ray Data.mp4", "01_lesson", None),
        ("02-3 Building a Ray Data-backed dataloader.mp4", "02_lesson", None),
        ("02-4 Preparing and Loading the Dataset for Ray Data.mp4", "03_lesson", None),
        ("02-5 Transformations with Ray Data.mp4", "04_lesson", None),
        ("02-6 Configuring TorchTrainer with Ray Data.mp4", "05_lesson", "part_1"),
        ("02-7 Launching Training with Ray Data.mp4", "06_lesson", "part_2"),
    ]

    custom: list[dict] = []
    videos: list[str] = []
    for filename, lesson_id, split_role in plan:
        rel = f"{subdir}/{filename}"
        if not (base / filename).is_file():
            continue
        videos.append(rel)
        lesson = lesson_by_id[lesson_id]
        entry: dict = {
            "video": rel,
            "lesson_id": lesson_id,
            "lesson_title": lesson["title"],
        }
        if split_role == "part_1":
            entry["split_from"] = full_backup
            entry["split_at_sec"] = split_at_sec
            entry["split_note"] = (
                f"First part of {full_backup}; launch step starts at {split_at_sec}s ({split_phrase!r})."
            )
        elif split_role == "part_2":
            entry["split_from"] = full_backup
            entry["split_at_sec"] = split_at_sec
            entry["split_note"] = (
                f"Second part of {full_backup}; from {split_at_sec}s ({split_phrase!r})."
            )
        custom.append(entry)

    return mapping_entry(
        course,
        mod_dir,
        "Ray Train Videos",
        video_subdir=subdir,
        videos=videos,
        notes=(
            "7 videos for 7 yaml lessons. Original 02-6 was split at 70.920s "
            f"({split_phrase!r}) into lesson 05 (TorchTrainer config) and lesson 06 (trainer.fit). "
            f"Full recording kept as {full_backup.split('/')[-1]}."
        ),
        custom_mappings=custom,
    )


def ray_serve_online_serving_mappings() -> dict | None:
    """Ray Example Workloads/03_ray_serve → workloads/Ray_Serve_Online_Serving/00_workload."""
    subdir = "Ray Example Workloads/03_ray_serve"
    base = VIDEOS_ROOT / subdir
    if not base.exists():
        return None

    course = "workloads/Ray_Serve_Online_Serving"
    mod_dir = "00_workload"
    mod = load_module_yaml(COURSES_ROOT / course / mod_dir / "module.yaml")
    if not mod:
        return None

    lesson_by_id = {l["lesson_id"]: l for l in mod["lessons"]}

    split_at_sec = 191.06
    full_backup = f"{subdir}/03 predict (full).mp4"
    split_phrase = "And then to wrap everything up"

    plan = [
        ("00 overview.mp4", "00_lesson", None),
        ("01 architecture imports.mp4", "01_lesson", None),
        ("02 deployment.mp4", "02_lesson", None),
        ("03 predict.mp4", "03_lesson", "part_1"),
        ("04 shutdown and summary.mp4", "04_lesson", "part_2"),
    ]

    custom: list[dict] = []
    videos: list[str] = []
    for filename, lesson_id, split_role in plan:
        rel = f"{subdir}/{filename}"
        if not (base / filename).is_file():
            continue
        videos.append(rel)
        lesson = lesson_by_id[lesson_id]
        entry: dict = {
            "video": rel,
            "lesson_id": lesson_id,
            "lesson_title": lesson["title"],
        }
        if split_role == "part_1":
            entry["split_from"] = full_backup
            entry["split_at_sec"] = split_at_sec
            entry["split_note"] = (
                f"First part of {full_backup}; shutdown/summary starts at {split_at_sec}s ({split_phrase!r})."
            )
        elif split_role == "part_2":
            entry["split_from"] = full_backup
            entry["split_at_sec"] = split_at_sec
            entry["split_note"] = (
                f"Second part of {full_backup}; from {split_at_sec}s ({split_phrase!r})."
            )
        custom.append(entry)

    return mapping_entry(
        course,
        mod_dir,
        "Ray Example Workloads",
        video_subdir=subdir,
        videos=videos,
        notes=(
            "5 videos for 5 yaml lessons. Original 03 predict.mp4 was split at 191.06s "
            f"({split_phrase!r}) into lesson 03 (testing) and lesson 04 (shutdown/summary). "
            f"Full recording kept as {full_backup.split('/')[-1]}."
        ),
        custom_mappings=custom,
    )


def pytorch_lightning_mappings() -> dict | None:
    """Ray Example Workloads/PyTorch Lightning → workloads/PyTorch_Lightning/00_workload."""
    subdir = "Ray Example Workloads/PyTorch Lightning"
    base = VIDEOS_ROOT / subdir
    if not base.exists():
        return None

    course = "workloads/PyTorch_Lightning"
    mod_dir = "00_workload"
    mod = load_module_yaml(COURSES_ROOT / course / mod_dir / "module.yaml")
    if not mod:
        return None

    lessons = mod["lessons"]
    lesson_by_id = {l["lesson_id"]: l for l in lessons}

    split_at_sec = 1169.218
    full_backup = f"{subdir}/03 ray train ddp (full).mp4"
    split_phrase = "All right. And then to wrap up and to finish this whole chapter"

    plan = [
        ("00 train intro.mp4", "00_lesson", None),
        ("01 when ray train.mp4", "01_lesson", None),
        ("02 pytorch.mp4", "02_lesson", None),
        ("03 ray train ddp.mp4", "03_lesson", "part_1"),
        ("04 ray train in production.mp4", "04_lesson", "part_2"),
    ]

    custom: list[dict] = []
    videos: list[str] = []
    for filename, lesson_id, split_role in plan:
        rel = f"{subdir}/{filename}"
        path = base / filename
        if not path.is_file():
            continue
        videos.append(rel)
        lesson = lesson_by_id[lesson_id]
        entry: dict = {
            "video": rel,
            "lesson_id": lesson_id,
            "lesson_title": lesson["title"],
        }
        if split_role == "part_1":
            entry["split_from"] = full_backup
            entry["split_at_sec"] = split_at_sec
            entry["split_note"] = f"First part of {full_backup}; outro starts at {split_at_sec}s ({split_phrase!r})."
        elif split_role == "part_2":
            entry["split_from"] = full_backup
            entry["split_at_sec"] = split_at_sec
            entry["split_note"] = f"Second part of {full_backup}; from {split_at_sec}s ({split_phrase!r})."
        custom.append(entry)

    return mapping_entry(
        course,
        mod_dir,
        "Ray Example Workloads",
        video_subdir=subdir,
        videos=videos,
        notes=(
            "5 videos for 5 yaml lessons. Original 03 ray train ddp.mp4 was split at 1169.218s "
            f"({split_phrase!r}) into lesson 03 (DDP) and lesson 04 (production outro). "
            f"Full recording kept as {full_backup.split('/')[-1]}."
        ),
        custom_mappings=custom,
    )


def count_active_videos() -> int:
    return sum(
        1
        for p in VIDEOS_ROOT.rglob("*.mp4")
        if LEGACY_PREFIX not in str(p.relative_to(VIDEOS_ROOT))
        and "(full)" not in p.name
    )


def main() -> None:
    mappings: list[dict] = []

    admin = "Getting Started with Anyscale for Administrators"
    for mod_dir, subdir in [
        ("02_00_Anyscale_Admin_Overview", "00 overview"),
        ("02_01_VM_vs_K8s", "01 vm vs k8s"),
        ("02_02a_Deploy_to_VM_AWS_EC2", "02 EC2"),
        ("02_03a_Deploy_to_K8s_New_AWS_EKS", "03 EKS"),
    ]:
        entry = module_mapping(
            "foundations/Anyscale_For_Admins", mod_dir, admin, f"{admin}/{subdir}"
        )
        if entry:
            mappings.append(entry)

    mappings.extend(anyscale_devs_mappings())

    llm = "LLM_course"
    llm_notes = {
        "00_intro_serve_llm": (
            "7 videos align 1:1 with yaml lessons 00–06. Video 1 is module intro; video 2 begins "
            "'What is LLM serving?' Notebook section numbers differ from yaml lesson order."
        ),
    }
    for i, mod_dir in enumerate(
        ["00_intro_serve_llm", "01_deploy_medium_llm", "02_advanced_llm_features"]
    ):
        entry = module_mapping(
            "foundations/LLM_Serving",
            mod_dir,
            llm,
            f"{llm}/Module {i + 1}",
            notes=llm_notes.get(mod_dir),
        )
        if entry:
            mappings.append(entry)

    entry = module_mapping(
        "foundations/Ray_AI_Libs",
        "00_intro",
        "Ray 101 Course",
        "Ray 101 Course/00_Introduction_to_Ray",
    )
    if entry:
        mappings.append(entry)

    for mod_dir, subdir in [
        ("01_Overview", "02_AI_Libs"),
        ("00_Basics", "01_Ray_Core"),
        ("01_Structured", "05_Ray_Data"),
        ("00_Serve", "06_Ray_Serve"),
    ]:
        course = {
            "01_Overview": "foundations/Ray_AI_Libs",
            "00_Basics": "foundations/Ray_Core",
            "01_Structured": "foundations/Ray_Data",
            "00_Serve": "foundations/Ray_Serve",
        }[mod_dir]
        entry = module_mapping(
            course, mod_dir, "Ray 101 Course", f"Ray 101 Course/{subdir}"
        )
        if entry:
            if mod_dir == "01_Overview":
                entry["notes"] = (
                    "Three videos align 1:1 with yaml lessons 00–02. Video 00 opens the full "
                    "notebook roadmap (7 sections) but covers lesson 00 in this recording."
                )
            elif mod_dir == "01_Structured":
                entry["notes"] = (
                    "Video 00 is module overview with roadmap. Video 06-08 covers yaml lesson 06; "
                    "notebook sections 7–8 may appear in the same recording."
                )
            elif mod_dir == "00_Basics":
                entry["notes"] = (
                    "Video 00 is module overview. Yaml lesson numbers (0–4) map to videos 01–04; "
                    "notebook section 3 has no separate yaml lesson."
                )
            elif mod_dir == "00_Serve":
                entry["notes"] = (
                    "Video 00 is module overview with 4-part roadmap. Videos 01–04 align with "
                    "yaml lessons 01–04."
                )
            mappings.append(entry)

    tune_entry = ray_tune_mappings()
    if tune_entry:
        mappings.append(tune_entry)

    rt = "Ray Train Videos"
    train_notes = {
        "01_intro": (
            "14 videos align 1:1 with yaml lessons 00–13. Supersedes removed Ray 101 Train "
            "conceptual videos. Yaml titles use notebook section numbers; sequential video "
            "order is authoritative."
        ),
        "03_fault_tolerance": (
            "7 videos map 1:1 to yaml lessons 00–06."
        ),
    }
    for mod_dir, subdir in [
        ("01_intro", "01 Introduction to Ray Train"),
        ("03_fault_tolerance", "03 Fault Tolerance in Ray Train"),
    ]:
        entry = module_mapping(
            "foundations/Ray_Train", mod_dir, rt, f"{rt}/{subdir}", notes=train_notes[mod_dir]
        )
        if entry:
            mappings.append(entry)

    rt_data_entry = ray_train_and_data_mappings()
    if rt_data_entry:
        mappings.append(rt_data_entry)

    re_base = "Ray Example Workloads"
    for course, subdir, notes in [
        ("Ray_Data_Batch_Inference", "01_batch_inference", None),
        ("Ray_Data_Processing", "02_data_processing", None),
        ("Ray_Distributed_Training", "04_ray_train", None),
    ]:
        entry = module_mapping(
            f"workloads/{course}", "00_workload", re_base, f"{re_base}/{subdir}", notes=notes
        )
        if entry:
            mappings.append(entry)

    serve_entry = ray_serve_online_serving_mappings()
    if serve_entry:
        mappings.append(serve_entry)

    pl_entry = pytorch_lightning_mappings()
    if pl_entry:
        mappings.append(pl_entry)

    workload_notes = {
        "Train_Vision_Pattern": (
            "Video 04a-2 covers imports and dataloading. Video 04a-8 fault-tolerance content "
            "confirmed by transcript (opening frame may show the next notebook section)."
        ),
        "Train_Rec_sys": (
            "Video 04e-2 covers imports and dataset load. Video 04e-5 checkpoint-resume "
            "confirmed by transcript."
        ),
    }
    for course, subdir in [
        ("Train_Vision_Pattern", "04a Computer Vision Workload"),
        ("Train_Tabular", "04b Tabular Workload"),
        ("Train_Time_Series", "04c Time Series Workload"),
        ("Train_Generative_CV", "04d1 Generative CV Workload"),
        ("Train_Policy_Learning", "04d2 Policy Learning Workload"),
        ("Train_Rec_sys", "04e RecSys Workload"),
    ]:
        entry = module_mapping(
            f"workloads/{course}",
            "00_workload",
            rt,
            f"{rt}/{subdir}",
            notes=workload_notes.get(course),
        )
        if entry:
            mappings.append(entry)

    devs = "Anyscale_for_Devs"
    result = {
        "version": "1.2",
        "description": (
            "Maps Thinkific/GDrive video assets to courses/ modules and lessons. "
            "Video-to-course direction only; not every course module has a video."
        ),
        "videos_root": "videos/Thinkific Course Videos",
        "statistics": {
            "total_videos_active": count_active_videos(),
            "total_videos_including_legacy": len(list(VIDEOS_ROOT.rglob("*.mp4"))),
            "mapped_modules": len(mappings),
        },
        "video_bundles": [
            {
                "id": "anyscale_admins",
                "video_folder": admin,
                "maps_to_courses": ["foundations/Anyscale_For_Admins"],
            },
            {
                "id": "anyscale_devs",
                "video_folder": devs,
                "maps_to_courses": ["foundations/Anyscale_Getting_Started"],
                "notes": "8 flat videos cover modules 00–06. Modules 07 (collaboration) and 08 (org setup) have no videos.",
            },
            {
                "id": "llm_serving",
                "video_folder": llm,
                "maps_to_courses": ["foundations/LLM_Serving"],
            },
            {
                "id": "ray_101",
                "video_folder": "Ray 101 Course",
                "maps_to_courses": [
                    "foundations/Ray_AI_Libs",
                    "foundations/Ray_Core",
                    "foundations/Ray_Data",
                    "foundations/Ray_Serve",
                    "foundations/Ray_Tune",
                ],
                "excludes": [LEGACY_PREFIX, "Ray 101 Course/03_Ray_Train (removed)"],
            },
            {
                "id": "ray_train_videos",
                "video_folder": rt,
                "description": (
                    "Ray Train foundations: 01 Introduction, 02 Integrating with Ray Data, "
                    "03 Fault Tolerance. Plus workload examples 04a-04e."
                ),
                "maps_to_courses": [
                    "foundations/Ray_Train",
                    "workloads/Train_Vision_Pattern",
                    "workloads/Train_Tabular",
                    "workloads/Train_Time_Series",
                    "workloads/Train_Generative_CV",
                    "workloads/Train_Policy_Learning",
                    "workloads/Train_Rec_sys",
                ],
            },
            {
                "id": "ray_example_workloads",
                "video_folder": re_base,
                "maps_to_courses": [
                    "workloads/Ray_Data_Batch_Inference",
                    "workloads/Ray_Data_Processing",
                    "workloads/Ray_Serve_Online_Serving",
                    "workloads/Ray_Distributed_Training",
                    "workloads/PyTorch_Lightning",
                ],
            },
        ],
        "course_mappings": mappings,
        "legacy_videos": {
            "path": LEGACY_PREFIX,
            "description": "Superseded exports. Safe to ignore for linking.",
        },
    }

    from enrich_video_mapping import enrich_course_mappings

    result = enrich_course_mappings(result)
    result["version"] = "1.3"

    with open(OUT, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")

    summary = result.get("validation_summary", {})
    print(
        f"Wrote {OUT} ({len(mappings)} modules, "
        f"{result['statistics']['total_videos_active']} active videos, "
        f"{summary.get('verified', 0)} verified / {summary.get('review', 0)} review)"
    )


if __name__ == "__main__":
    main()
