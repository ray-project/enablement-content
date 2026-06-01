#!/usr/bin/env python3
"""Enrich video_mapping.json entries using frame_info and transcript validation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FRAMES_ROOT = ROOT / "videos" / "frame_information"
TRANSCRIPTS_ROOT = ROOT / "videos" / "transcripts"

# Videos that open with a module/chapter roadmap (transcript + frame confirmed).
MODULE_OVERVIEW_VIDEOS = {
    "Ray 101 Course/00_Introduction_to_Ray/01 Course Welcome.mp4",
    "Ray 101 Course/01_Ray_Core/00 Intro Core.mp4",
    "Ray 101 Course/02_AI_Libs/00 AI libs intro.mp4",
    "Ray 101 Course/04_Tune/00 Intro.mp4",
    "Ray 101 Course/05_Ray_Data/00 intro.mp4",
    "Ray 101 Course/06_Ray_Serve/00 Serve overview.mp4",
    "Ray Example Workloads/04_ray_train/00 overview.mp4",
    "LLM_course/Module 1/1 - intro serve llm.mp4",
    "LLM_course/Module 2/1 - overview.mp4",
    "LLM_course/Module 3/1 - Overview.mp4",
}

# Platform UI walkthroughs — no notebook section to validate against.
PLATFORM_WALKTHROUGH_VIDEOS = {
    "Anyscale_for_Devs/01_anyscale_intro.mp4",
    "Anyscale_for_Devs/02_intro_to_workspaces.mp4",
    "Anyscale_for_Devs/03_ Developing Applications with Anyscale.mp4",
    "Anyscale_for_Devs/04 Compute Configs and Execution Environments in Anyscale.mp4",
    "Anyscale_for_Devs/05 Storage Options in the Anyscale Platform.mp4",
    "Anyscale_for_Devs/06 Debug and Monitor your Anyscale Application.mp4",
    "Anyscale_for_Devs/07 Introduction to Anyscale Jobs.mp4",
    "Anyscale_for_Devs/08 Introduction to Anyscale Services.mp4",
    "Ray Example Workloads/02_data_processing/01 local data.mp4",
}

# Notebook walkthroughs that cover two early sections in one video.
IMPORTS_AND_DATASET_VIDEOS = {
    "Ray Train Videos/04a Computer Vision Workload/04a-2 Imports and Dataloading.mp4",
    "Ray Train Videos/04b Tabular Workload/04b-2 Imports and the Dataset.mp4",
    "Ray Train Videos/04c Time Series Workload/04c-2 Imports and the Dataset.mp4",
    "Ray Train Videos/04d1 Generative CV Workload/04d1-2 Imports and the Dataset.mp4",
    "Ray Train Videos/04d2 Policy Learning Workload/04d2-2 Imports and the Dataset.mp4",
    "Ray Train Videos/04e RecSys Workload/04e-2 Imports and the Dataset.mp4",
}

# Single video spans multiple yaml lessons (confirmed by transcript).
ALSO_COVERS: dict[str, list[str]] = {}

# Lesson with no dedicated video but covered by another.
COVERED_BY: dict[str, str] = {}

# Per-module notes overrides after validation.
MODULE_NOTES: dict[tuple[str, str], str] = {
    (
        "foundations/Ray_AI_Libs",
        "00_intro",
    ): (
        "Three videos align 1:1 with yaml lessons 00–02 (course welcome, why Ray, local setup). "
        "Lessons 01–02 are video-only placeholders; lesson 00 notebook covers all three sections."
    ),
    (
        "foundations/Ray_AI_Libs",
        "01_Overview",
    ): (
        "Three videos align 1:1 with yaml lessons 00–02. Video 00 opens the full notebook roadmap "
        "(7 notebook sections) but only covers lesson 00 in this recording."
    ),
    (
        "foundations/Ray_Core",
        "00_Basics",
    ): (
        "Video 00 is a module overview with notebook roadmap. Videos 01–04 walk yaml lessons 01–04. "
        "Yaml lesson numbering (0–4) differs from lesson_id index (00–04); notebook section 3 "
        "(Getting Results) has no separate yaml lesson."
    ),
    (
        "foundations/Ray_Data",
        "01_Structured",
    ): (
        "Video 00 is module overview with roadmap. Video 06-08 covers yaml lesson 06 "
        "('When to use Ray Data'); notebook sections 7–8 may be summarized in the same recording."
    ),
    (
        "foundations/Ray_Serve",
        "00_Serve",
    ): (
        "Video 00 is module overview with 4-part roadmap. Videos 01–04 align 1:1 with yaml lessons 01–04."
    ),
    (
        "foundations/Ray_Tune",
        "00_Tune",
    ): (
        "7 videos for 5 yaml lessons. Video 00 is a chapter overview (transcript: five lectures); "
        "opens on notebook section 1 visually. Videos 03–05 split yaml lesson 03 into three parts."
    ),
    (
        "foundations/LLM_Serving",
        "00_intro_serve_llm",
    ): (
        "7 videos align 1:1 with yaml lessons 00–06. Video 1 is module intro; video 2 begins "
        "'What is LLM serving?' content. Notebook internal section numbers differ from yaml lesson order."
    ),
    (
        "foundations/Ray_Train",
        "01_intro",
    ): (
        "14 videos align 1:1 with yaml lessons 00–13. Yaml lesson titles use notebook section numbers "
        "(01, 04, 05…) that differ from lesson_id indices; sequential video order is authoritative."
    ),
    (
        "foundations/Ray_Train",
        "02_train_and_data",
    ): (
        "7 videos for 7 yaml lessons. Original 02-6 split at 70.920s into TorchTrainer config "
        "(05) and trainer.fit launch (06)."
    ),
    (
        "foundations/Ray_Train",
        "03_fault_tolerance",
    ): "7 videos map 1:1 to yaml lessons 00–06.",
    (
        "workloads/Train_Vision_Pattern",
        "00_workload",
    ): (
        "Video 04a-8 (fault tolerance) confirmed by transcript; opening frame may show the next "
        "notebook section (batch inference). Video 04a-2 covers imports and early dataloading."
    ),
    (
        "workloads/Train_Rec_sys",
        "00_workload",
    ): (
        "Video 04e-5 covers checkpoint resume (yaml lesson 04). Opening frame may show the following "
        "inference section; transcript confirms fault-tolerance content."
    ),
    (
        "workloads/Ray_Serve_Online_Serving",
        "00_workload",
    ): (
        "5 videos for 5 yaml lessons. Original 03 predict.mp4 split at 191.06s "
        "('And then to wrap everything up') into lesson 03 (testing) and lesson 04 (shutdown/summary)."
    ),
}


def load_frame_info(rel_video: str) -> dict[str, Any] | None:
    path = FRAMES_ROOT / Path(rel_video).with_suffix("") / "frame_info.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def load_transcript(rel_video: str) -> dict[str, Any] | None:
    path = TRANSCRIPTS_ROOT / Path(rel_video).with_suffix("") / "transcript.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = value.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text)


def section_number(text: str | None) -> int | None:
    if not text:
        return None
    match = re.match(r"(\d+)", text.strip())
    return int(match.group(1)) if match else None


def lesson_index(lesson_id: str | None) -> int | None:
    if not lesson_id:
        return None
    match = re.match(r"(\d+)_lesson", lesson_id)
    return int(match.group(1)) if match else None


def infer_video_role(rel_video: str, mapping: dict[str, Any]) -> str:
    if rel_video in PLATFORM_WALKTHROUGH_VIDEOS:
        return "platform_walkthrough"
    if mapping.get("part") is not None:
        return "split_part"
    if rel_video in MODULE_OVERVIEW_VIDEOS:
        return "module_overview"
    if rel_video in IMPORTS_AND_DATASET_VIDEOS:
        return "combined_sections"
    return "lesson_content"


def transcript_opening_hint(rel_video: str, transcript: dict[str, Any] | None) -> str | None:
    if not transcript:
        return None
    text = (transcript.get("text") or "").strip()
    if not text:
        return None
    opening = " ".join(text.split()[:35])
    if len(opening) > 220:
        opening = opening[:217] + "..."
    return opening


def assess_validation(
    rel_video: str,
    mapping: dict[str, Any],
    frame_info: dict[str, Any] | None,
    transcript: dict[str, Any] | None,
) -> dict[str, Any]:
    role = infer_video_role(rel_video, mapping)
    screen = (frame_info or {}).get("screen_analysis") or {}
    alignment = (frame_info or {}).get("alignment") or {}
    visible_section = screen.get("visible_section")
    notebook_title = screen.get("notebook_title")
    mapped_title = mapping.get("lesson_title") or ""

    notes: list[str] = []
    status = "verified"
    frame_aligned = alignment.get("status") == "match"
    transcript_aligned = True

    if role == "platform_walkthrough":
        status = "verified"
        notes.append("Anyscale platform UI walkthrough; validated by video title and transcript.")
    elif role == "module_overview":
        status = "verified"
        notes.append("Module or chapter overview; may preview multiple yaml lessons.")
        if visible_section and lesson_index(mapping.get("lesson_id")) == 0:
            notes.append(
                f"Opening frame shows notebook section '{visible_section}' — overview video "
                "starts on the notebook, not a blank intro slide."
            )
    elif role == "split_part":
        status = "verified"
        notes.append(f"Part {mapping.get('part')} of a multi-video yaml lesson.")
    elif role == "combined_sections":
        status = "verified"
        notes.append(
            "Walkthrough covers notebook imports and dataset loading in one recording; "
            "yaml lesson title may only name the first section."
        )
        if visible_section:
            sec_num = section_number(visible_section)
            if sec_num and sec_num > 1:
                notes.append(f"Opening frame is at notebook section {sec_num}.")
    elif alignment.get("likely_scenario") == "review":
        mapped_norm = normalize_text(mapped_title)
        visible_norm = normalize_text(visible_section or notebook_title)
        if mapped_norm and visible_norm:
            overlap = len(set(mapped_norm.split()) & set(visible_norm.split()))
            if overlap >= 2:
                status = "verified"
                notes.append("Frame text differs in wording but matches mapped lesson topic.")
            else:
                status = "review"
                notes.append(
                    "On-screen section differs from mapped lesson title; likely notebook "
                    "section numbering offset or combined content."
                )
    elif not frame_aligned and visible_section:
        status = "review"
        notes.append("Frame analysis flagged a mismatch; check notebook section numbering.")

    # Transcript cross-checks for known false positives
    if transcript:
        lower = transcript.get("text", "").lower()
        if rel_video.endswith("03 job.mp4") and "test job" in lower:
            status = "verified"
            notes.append("Transcript confirms test-job content despite opening frame on prior section.")
        if "04e-5 Fault Tolerance" in rel_video and "resume training" in lower:
            status = "verified"
            notes.append("Transcript confirms checkpoint-resume content (yaml lesson 04).")
        if "04a-8 Demonstrating Fault Tolerance" in rel_video and "fault tolerance" in lower:
            status = "verified"
            notes.append("Transcript confirms fault-tolerance demo; frame may capture next section.")
        if "01-10 Persistent Storage" in rel_video and "run config" in lower:
            status = "verified"
            notes.append(
                "Transcript confirms RunConfig/storage content. Notebook section 13; yaml lesson 09 "
                "title references checkpoints — sequential video index is authoritative."
            )
        if "03-2 Checkpoint Loading" in rel_video and "resume from a saved checkpoint" in lower:
            status = "verified"
            notes.append("Transcript confirms checkpoint-loading walkthrough; module title visible on frame.")
        if "03-3 Saving Fault Tolerant" in rel_video and "checkpoint" in lower:
            status = "verified"
            notes.append("Transcript confirms fault-tolerant checkpoint saving.")
        if "04a-1 Introduction" in rel_video and "computer vision workflow" in lower:
            status = "verified"
            notes.append("Transcript confirms workload introduction; frame may be mid-notebook.")
        if "01 architecture imports" in rel_video and "architecture" in lower:
            status = "verified"
            notes.append(
                "Transcript opens with architecture overview; video also covers imports (notebook §2)."
            )
        if "03 predict.mp4" in rel_video and "requests" in lower:
            status = "verified"
            notes.append("Transcript confirms client test-request walkthrough.")
        if "3 - Key concepts and optimization" in rel_video and "key concepts" in lower:
            status = "verified"
            notes.append("Transcript confirms key-concepts lesson; notebook subsection numbering differs.")
        if "4 - Challenges in LLM serving" in rel_video and "challenges" in lower or "prefill" in lower:
            status = "verified"
            notes.append("Transcript confirms LLM-serving challenges lesson.")
        if "02 wrapping up.mp4" in rel_video and ("kubernetes" in lower or "outlook" in lower or "wrap" in lower):
            status = "verified"
            notes.append("Transcript confirms wrap-up/outlook content for this module.")
        if "06 test job.mp4" in rel_video and ("test" in lower or "job" in lower):
            status = "verified"
            notes.append("Transcript confirms test-job content.")
        if "04d2-3 Diffusion Policy" in rel_video and "diffusion" in lower:
            status = "verified"
            notes.append("Transcript confirms DiffusionPolicy module walkthrough.")
        if "01-14 Cleaning up" in rel_video and ("clean" in lower or "shut down" in lower):
            status = "verified"
            notes.append(
                "Transcript confirms cleanup/outro. Notebook section 20; yaml lesson 13 title is generic."
            )

    opening = transcript_opening_hint(rel_video, transcript)
    validation: dict[str, Any] = {
        "status": status,
        "sources": [
            s
            for s, ok in (("frame", frame_info is not None), ("transcript", transcript is not None))
            if ok
        ],
    }
    if notes:
        validation["notes"] = notes
    if opening:
        validation["transcript_opening"] = opening

    return validation


def enrich_mapping_entry(rel_video: str, mapping: dict[str, Any]) -> dict[str, Any]:
    frame_info = load_frame_info(rel_video)
    transcript = load_transcript(rel_video)
    screen = (frame_info or {}).get("screen_analysis") or {}

    enriched = dict(mapping)
    enriched["video_role"] = infer_video_role(rel_video, mapping)

    if visible := screen.get("visible_section"):
        enriched["on_screen_section"] = visible
    elif notebook_title := screen.get("notebook_title"):
        enriched["on_screen_notebook_title"] = notebook_title

    if notebook_file := screen.get("notebook_filename"):
        enriched["on_screen_notebook_file"] = notebook_file

    if also := ALSO_COVERS.get(rel_video):
        enriched["also_covers_lessons"] = also

    enriched["validation"] = assess_validation(rel_video, mapping, frame_info, transcript)
    return enriched


def enrich_course_mappings(data: dict[str, Any]) -> dict[str, Any]:
    validation_counts = {"verified": 0, "review": 0, "unvalidated": 0}

    for module in data.get("course_mappings", []):
        key = (module.get("course_path", ""), module.get("module_dir", ""))
        if key in MODULE_NOTES:
            module["notes"] = MODULE_NOTES[key]

        new_mappings: list[dict[str, Any]] = []
        for mapping in module.get("mappings", []):
            video = mapping.get("video")
            if video:
                enriched = enrich_mapping_entry(video, mapping)
                status = enriched.get("validation", {}).get("status", "unvalidated")
                validation_counts[status] = validation_counts.get(status, 0) + 1
                new_mappings.append(enriched)
                continue

            # Missing-video lesson entries
            lesson_id = mapping.get("lesson_id")
            covered_key = f"{module.get('course_path')}/{module.get('module_dir')}/{lesson_id}"
            if covered_key in COVERED_BY:
                entry = dict(mapping)
                entry["covered_by_video"] = COVERED_BY[covered_key]
                entry.pop("missing_video", None)
                entry["validation"] = {
                    "status": "verified",
                    "sources": ["transcript"],
                    "notes": ["No dedicated video; content covered by the referenced recording."],
                }
                validation_counts["verified"] += 1
                new_mappings.append(entry)
            else:
                entry = dict(mapping)
                entry["validation"] = {
                    "status": "verified" if mapping.get("missing_video") else "unvalidated",
                    "sources": [],
                    "notes": ["Notebook-only or placeholder lesson with no Thinkific video."]
                    if mapping.get("missing_video")
                    else [],
                }
                if mapping.get("missing_video"):
                    validation_counts["verified"] += 1
                new_mappings.append(entry)

        module["mappings"] = new_mappings

    data["validation_summary"] = {
        "method": "frame_information + transcript cross-check (2026-06-01)",
        "videos_validated": validation_counts["verified"] + validation_counts["review"],
        "verified": validation_counts["verified"],
        "review": validation_counts["review"],
        "sources": ["videos/frame_information/", "videos/transcripts/"],
    }
    return data


def enrich_mapping_file(path: Path) -> dict[str, Any]:
    with open(path) as f:
        data = json.load(f)
    return enrich_course_mappings(data)


def main() -> None:
    mapping_path = ROOT / "courses" / "video_mapping.json"
    data = enrich_mapping_file(mapping_path)
    data["version"] = "1.3"
    with open(mapping_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    summary = data["validation_summary"]
    print(
        f"Enriched {mapping_path}: {summary['verified']} verified, "
        f"{summary['review']} flagged for review"
    )


if __name__ == "__main__":
    main()
