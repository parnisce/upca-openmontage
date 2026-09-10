"""Canonical paths for the UPCA application layer."""

from __future__ import annotations

from pathlib import Path

from lib.paths import PROJECTS_DIR, REPO_ROOT

UPCA_ROOT = REPO_ROOT / "upca"
CATALOG_DIR = UPCA_ROOT / "catalog"
SEED_DIR = UPCA_ROOT / "seed"
RUNTIME_DIR = CATALOG_DIR / "runtime"
MEDIA_UPLOADS = CATALOG_DIR / "media" / "uploads"
TEMPLATES_DIR = UPCA_ROOT / "templates"

PROPERTIES_FILE = RUNTIME_DIR / "properties.json"
AGENTS_FILE = RUNTIME_DIR / "agents.json"
MEDIA_INDEX_FILE = RUNTIME_DIR / "media.json"
JOBS_FILE = RUNTIME_DIR / "jobs.json"
SETTINGS_FILE = RUNTIME_DIR / "settings.json"

PIPELINE_TYPE = "upca-real-estate"
STYLE_PLAYBOOK = "upca-brand"

FORMAT_PROFILES = {
    "16:9": "youtube_landscape",
    "9:16": "instagram_reels",
    "1:1": "instagram_feed",
}

FORMAT_RESOLUTIONS = {
    "16:9": "1920x1080",
    "9:16": "1080x1920",
    "1:1": "1080x1080",
}

JOB_STATUSES = (
    "Draft",
    "Preparing",
    "Script",
    "Assets",
    "Voiceover",
    "Composition",
    "Rendering",
    "Review",
    "Completed",
    "Failed",
)


def ensure_runtime_dirs() -> None:
    for path in (RUNTIME_DIR, MEDIA_UPLOADS, TEMPLATES_DIR):
        path.mkdir(parents=True, exist_ok=True)


__all__ = [
    "REPO_ROOT",
    "PROJECTS_DIR",
    "UPCA_ROOT",
    "CATALOG_DIR",
    "SEED_DIR",
    "RUNTIME_DIR",
    "MEDIA_UPLOADS",
    "TEMPLATES_DIR",
    "PROPERTIES_FILE",
    "AGENTS_FILE",
    "MEDIA_INDEX_FILE",
    "JOBS_FILE",
    "SETTINGS_FILE",
    "PIPELINE_TYPE",
    "STYLE_PLAYBOOK",
    "FORMAT_PROFILES",
    "FORMAT_RESOLUTIONS",
    "JOB_STATUSES",
    "ensure_runtime_dirs",
]
