"""Create OpenMontage projects and write canonical artifacts + checkpoints."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from lib.checkpoint import init_project, write_checkpoint
from lib.paths import PROJECTS_DIR
from schemas.artifacts import validate_artifact
from upca.paths import PIPELINE_TYPE, STYLE_PLAYBOOK


def create_openmontage_project(project_id: str, title: str) -> Path:
    return init_project(
        project_id,
        title=title,
        pipeline_type=PIPELINE_TYPE,
        style_playbook=STYLE_PLAYBOOK,
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def copy_media_into_project(project_dir: Path, package: dict[str, Any]) -> dict[str, str]:
    """Copy catalog files into the project workspace. Returns abs→rel map."""
    copied: dict[str, str] = {}
    media = package.get("media") or {}
    groups = {
        "exteriorPhotos": ("images", "ext"),
        "interiorPhotos": ("images", "int"),
        "videoClips": ("video", "clip"),
    }

    def copy_one(source: str, folder: str, stem: str) -> str:
        src = Path(source)
        if not src.is_file():
            return source
        dest_dir = project_dir / "assets" / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{stem}{src.suffix.lower()}"
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        rel = dest.relative_to(project_dir).as_posix()
        copied[str(src)] = rel
        copied[str(src.resolve())] = rel
        return rel

    next_media = {
        "exteriorPhotos": [],
        "interiorPhotos": [],
        "videoClips": [],
        "agentPhoto": "",
        "agentLogo": "",
    }
    for key, (folder, prefix) in groups.items():
        for index, path in enumerate(media.get(key) or []):
            next_media[key].append(copy_one(str(path), folder, f"{prefix}_{index + 1:02d}"))
    if media.get("agentPhoto"):
        next_media["agentPhoto"] = copy_one(str(media["agentPhoto"]), "images", "agent")
        package["agent"]["photo"] = next_media["agentPhoto"]
    if media.get("agentLogo"):
        next_media["agentLogo"] = copy_one(str(media["agentLogo"]), "images", "logo")
    package["media"] = next_media
    return copied


def persist_artifacts(project_dir: Path, artifacts: dict[str, dict[str, Any]]) -> None:
    for name, payload in artifacts.items():
        if name in {"research_brief", "proposal_packet", "brief", "script", "scene_plan",
                    "asset_manifest", "edit_decisions", "render_report", "publish_log",
                    "upca_package", "final_review"}:
            validate_artifact(name, payload)
        write_json(project_dir / "artifacts" / f"{name}.json", payload)


def complete_stage(
    project_id: str,
    stage: str,
    artifacts: dict[str, Any],
    *,
    metadata: dict[str, Any] | None = None,
) -> Path:
    return write_checkpoint(
        PROJECTS_DIR,
        project_id,
        stage,
        "completed",
        artifacts,
        pipeline_type=PIPELINE_TYPE,
        style_playbook=STYLE_PLAYBOOK,
        human_approved=True,
        metadata=metadata,
    )


def fail_stage(project_id: str, stage: str, error: str) -> Path:
    return write_checkpoint(
        PROJECTS_DIR,
        project_id,
        stage,
        "failed",
        {},
        pipeline_type=PIPELINE_TYPE,
        style_playbook=STYLE_PLAYBOOK,
        error=error,
    )


def mark_in_progress(project_id: str, stage: str, artifacts: dict[str, Any] | None = None) -> Path:
    return write_checkpoint(
        PROJECTS_DIR,
        project_id,
        stage,
        "in_progress",
        artifacts or {},
        pipeline_type=PIPELINE_TYPE,
        style_playbook=STYLE_PLAYBOOK,
    )
