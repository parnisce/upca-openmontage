"""Map OpenMontage checkpoints onto UPCA job statuses."""

from __future__ import annotations

from typing import Any

STAGE_TO_STATUS = {
    "idea": "Preparing",
    "script": "Script",
    "scene_plan": "Assets",
    "assets": "Assets",
    "edit": "Composition",
    "compose": "Rendering",
    "publish": "Completed",
}


def derive_status(job: dict[str, Any], checkpoints: dict[str, dict[str, Any]]) -> str:
    if job.get("status") == "Failed" or any(
        item.get("status") == "failed" for item in checkpoints.values()
    ):
        return "Failed"
    compose = checkpoints.get("compose") or {}
    if compose.get("status") == "completed":
        if (checkpoints.get("publish") or {}).get("status") == "completed":
            return "Completed"
        return "Review"
    if compose.get("status") == "in_progress":
        return "Rendering"
    if (checkpoints.get("edit") or {}).get("status") == "completed":
        return "Composition"
    if (checkpoints.get("assets") or {}).get("status") in {"completed", "in_progress"}:
        voice = ((checkpoints.get("assets") or {}).get("metadata") or {}).get("voiceover")
        if voice == "pending":
            return "Voiceover"
        return "Assets"
    if (checkpoints.get("script") or {}).get("status") == "completed":
        return "Assets"
    if (checkpoints.get("script") or {}).get("status") == "in_progress":
        return "Script"
    if (checkpoints.get("idea") or {}).get("status") in {"completed", "in_progress"}:
        return "Preparing"
    return job.get("status") or "Draft"
