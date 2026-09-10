"""Create video jobs and run the template factory through OpenMontage."""

from __future__ import annotations

import re
import threading
import uuid
from pathlib import Path
from typing import Any

from lib.paths import PROJECTS_DIR
from upca.paths import FORMAT_PROFILES
from upca.services import catalog
from upca.services import project_bridge
from upca.services import template_compiler as compiler

_LOCK = threading.Lock()
_THREADS: dict[str, threading.Thread] = {}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:40] or "listing"


def _require(row: dict[str, Any] | None, label: str) -> dict[str, Any]:
    if not row:
        raise ValueError(f"{label} not found")
    return row


def create_job(payload: dict[str, Any]) -> dict[str, Any]:
    property_row = _require(catalog.get_property(payload["propertyId"]), "Property")
    agent_row = _require(catalog.get_agent(payload["agentId"]), "Agent")
    template = _require(catalog.get_template(payload.get("templateId") or "just-listed"), "Template")
    format_name = payload.get("format") or catalog.get_settings().get("defaultFormat") or "9:16"
    if format_name not in FORMAT_PROFILES:
        raise ValueError(f"Unsupported format {format_name!r}")
    if not property_row.get("address") or not property_row.get("city") or not property_row.get("price"):
        raise ValueError("Property needs address, city, and price")

    project_id = f"upca-{_slug(property_row['address'])}-{uuid.uuid4().hex[:6]}"
    title = f"{template.get('name')} — {property_row['address']}"
    job = catalog.save_job(
        {
            "id": f"job-{uuid.uuid4().hex[:8]}",
            "projectId": project_id,
            "propertyId": property_row["id"],
            "agentId": agent_row["id"],
            "templateId": template["id"],
            "format": format_name,
            "status": "Draft",
            "title": title,
            "error": "",
            "outputPath": "",
            "orchestration": "template",
        }
    )
    return job


def prepare_job(job_id: str) -> dict[str, Any]:
    job = _require(catalog.get_job(job_id), "Job")
    property_row = _require(catalog.get_property(job["propertyId"]), "Property")
    agent_row = _require(catalog.get_agent(job["agentId"]), "Agent")
    template = _require(catalog.get_template(job["templateId"]), "Template")
    settings = catalog.get_settings()

    catalog.save_job({**job, "status": "Preparing", "error": ""})
    project_dir = project_bridge.create_openmontage_project(job["projectId"], job["title"])

    media_ids = property_row.get("mediaIds") or {}
    project_media = {
        "exteriorPhotos": compiler.resolve_media_ids(media_ids.get("exteriorPhotos")),
        "interiorPhotos": compiler.resolve_media_ids(media_ids.get("interiorPhotos")),
        "videoClips": compiler.resolve_media_ids(media_ids.get("videoClips")),
        "agentPhoto": compiler.resolve_media_ids([agent_row.get("photoMediaId") or ""])[:1],
        "agentLogo": compiler.resolve_media_ids([agent_row.get("logoMediaId") or ""])[:1],
    }
    if project_media["agentPhoto"]:
        project_media["agentPhoto"] = project_media["agentPhoto"][0]
    else:
        project_media["agentPhoto"] = ""
    if project_media["agentLogo"]:
        project_media["agentLogo"] = project_media["agentLogo"][0]
    else:
        project_media["agentLogo"] = ""

    package = compiler.build_package(
        template=template,
        property_row=property_row,
        agent_row=agent_row,
        settings=settings,
        format_name=job["format"],
        project_media=project_media,
    )
    copied = project_bridge.copy_media_into_project(project_dir, package)
    brief = compiler.build_brief(package, template)
    script = compiler.build_script(package, template)
    scene_plan = compiler.build_scene_plan(package, template)
    asset_manifest = compiler.build_asset_manifest(package, copied)
    edit_decisions = compiler.build_edit_decisions(package, template, asset_manifest)

    project_bridge.persist_artifacts(
        project_dir,
        {
            "upca_package": package,
            "brief": brief,
            "script": script,
            "scene_plan": scene_plan,
            "asset_manifest": asset_manifest,
            "edit_decisions": edit_decisions,
        },
    )
    project_bridge.complete_stage(job["projectId"], "idea", {"brief": brief})
    catalog.save_job({**job, "status": "Script"})
    project_bridge.complete_stage(job["projectId"], "script", {"script": script})
    catalog.save_job({**job, "status": "Assets"})
    project_bridge.complete_stage(job["projectId"], "scene_plan", {"scene_plan": scene_plan})
    project_bridge.complete_stage(
        job["projectId"],
        "assets",
        {"asset_manifest": asset_manifest},
        metadata={"voiceover": "skipped"},
    )
    catalog.save_job({**job, "status": "Composition"})
    project_bridge.complete_stage(job["projectId"], "edit", {"edit_decisions": edit_decisions})
    return catalog.save_job({**job, "status": "Composition", "error": ""})


def render_job(job_id: str, previous_status: str | None = None) -> dict[str, Any]:
    job = _require(catalog.get_job(job_id), "Job")
    project_dir = PROJECTS_DIR / job["projectId"]
    if not (project_dir / "artifacts" / "edit_decisions.json").exists():
        job = prepare_job(job_id)

    if previous_status is None:
        previous_status = job.get("status")
    catalog.save_job({**job, "status": "Rendering", "error": ""})
    project_bridge.mark_in_progress(job["projectId"], "compose")

    from tools.video.video_compose import VideoCompose

    edit_decisions = _read_json(project_dir / "artifacts" / "edit_decisions.json")
    asset_manifest = _absolutize_manifest(
        _read_json(project_dir / "artifacts" / "asset_manifest.json"),
        project_dir,
    )
    scene_plan = _read_json(project_dir / "artifacts" / "scene_plan.json")
    package = _absolutize_package(
        _read_json(project_dir / "artifacts" / "upca_package.json"),
        project_dir,
    )
    if isinstance(edit_decisions.get("metadata"), dict):
        edit_decisions["metadata"]["upca"] = package
    output_path = project_dir / "renders" / "final.mp4"
    profile = FORMAT_PROFILES[job["format"]]

    tool = VideoCompose()
    reused_output = False
    result_error = ""
    if (
        previous_status == "Completed"
        and output_path.exists()
        and output_path.stat().st_size > 1024
    ):
        review = tool._run_final_review(output_path, edit_decisions)
        if review.get("status") != "fail":
            reused_output = True
        else:
            result = tool.execute(
                {
                    "operation": "render",
                    "edit_decisions": edit_decisions,
                    "asset_manifest": asset_manifest,
                    "scene_plan": scene_plan.get("scenes") or [],
                    "profile": profile,
                    "output_path": str(output_path),
                }
            )
            if not result.success:
                result_error = result.error or "Render failed"
    else:
        result = tool.execute(
            {
                "operation": "render",
                "edit_decisions": edit_decisions,
                "asset_manifest": asset_manifest,
                "scene_plan": scene_plan.get("scenes") or [],
                "profile": profile,
                "output_path": str(output_path),
            }
        )
        if not result.success:
            result_error = result.error or "Render failed"

    if not reused_output and result_error:
        project_bridge.fail_stage(job["projectId"], "compose", result_error)
        return catalog.save_job({**job, "status": "Failed", "error": result_error})

    render_report = {
        "version": "1.0",
        "outputs": [
            {
                "path": str(output_path.relative_to(project_dir)).replace("\\", "/"),
                "format": "mp4",
                "codec": "libx264",
                "resolution": package["video"]["resolution"],
                "duration_seconds": package["video"]["duration"],
                "fps": package["video"]["fps"],
                "platform_target": profile,
            }
        ],
        "render_grammar": "upca-just-listed",
        "warnings": [],
    }
    publish_log = compiler.build_publish_log(package, str(output_path))
    project_bridge.persist_artifacts(
        project_dir,
        {"render_report": render_report, "publish_log": publish_log},
    )
    project_bridge.complete_stage(
        job["projectId"],
        "compose",
        {"render_report": render_report},
    )
    project_bridge.complete_stage(
        job["projectId"],
        "publish",
        {"publish_log": publish_log},
    )
    return catalog.save_job(
        {
            **job,
            "status": "Completed",
            "outputPath": str(output_path),
            "error": "",
        }
    )


def _project_abs(project_dir: Path, value: str) -> str:
    if not value:
        return value
    path = Path(value)
    if path.is_absolute():
        return str(path)
    candidate = (project_dir / value).resolve()
    return str(candidate) if candidate.exists() else value


def _absolutize_manifest(manifest: dict[str, Any], project_dir: Path) -> dict[str, Any]:
    next_manifest = dict(manifest)
    assets = []
    for asset in manifest.get("assets") or []:
        row = dict(asset)
        row["path"] = _project_abs(project_dir, str(row.get("path") or ""))
        assets.append(row)
    next_manifest["assets"] = assets
    return next_manifest


def _absolutize_package(package: dict[str, Any], project_dir: Path) -> dict[str, Any]:
    next_package = dict(package)
    media = dict(package.get("media") or {})
    for key in ("exteriorPhotos", "interiorPhotos", "videoClips"):
        media[key] = [_project_abs(project_dir, str(item)) for item in media.get(key) or []]
    for key in ("agentPhoto", "agentLogo"):
        media[key] = _project_abs(project_dir, str(media.get(key) or ""))
    next_package["media"] = media
    agent = dict(package.get("agent") or {})
    if agent.get("photo"):
        agent["photo"] = _project_abs(project_dir, str(agent["photo"]))
    next_package["agent"] = agent
    return next_package


def _read_json(path: Path) -> dict[str, Any]:
    import json

    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def start_render_async(job_id: str) -> dict[str, Any]:
    job = _require(catalog.get_job(job_id), "Job")
    original_status = job.get("status")
    catalog.save_job({**job, "status": "Rendering", "error": ""})

    def _run() -> None:
        with _LOCK:
            try:
                render_job(job_id, previous_status=original_status)
            except Exception as exc:  # noqa: BLE001 — persist failure for the dashboard
                current = catalog.get_job(job_id) or job
                catalog.save_job({**current, "status": "Failed", "error": str(exc)})
                try:
                    project_bridge.fail_stage(current["projectId"], "compose", str(exc))
                except Exception:
                    pass

    thread = threading.Thread(target=_run, name=f"upca-render-{job_id}", daemon=True)
    _THREADS[job_id] = thread
    thread.start()
    return catalog.get_job(job_id) or job
