"""JSON catalog for properties, agents, media, jobs, and settings."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from upca.paths import (
    AGENTS_FILE,
    JOBS_FILE,
    MEDIA_INDEX_FILE,
    MEDIA_UPLOADS,
    PROPERTIES_FILE,
    SEED_DIR,
    SETTINGS_FILE,
    TEMPLATES_DIR,
    ensure_runtime_dirs,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, list) else []


def _write_list(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)


def _read_object(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else dict(default)


def _write_object(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def _seed_if_missing(dest: Path, seed_name: str) -> None:
    if dest.exists():
        return
    source = SEED_DIR / seed_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        shutil.copyfile(source, dest)


def bootstrap_catalog() -> None:
    ensure_runtime_dirs()
    _seed_if_missing(PROPERTIES_FILE, "properties.json")
    _seed_if_missing(AGENTS_FILE, "agents.json")
    _seed_if_missing(SETTINGS_FILE, "settings.json")
    if not MEDIA_INDEX_FILE.exists():
        _write_list(MEDIA_INDEX_FILE, [])
    if not JOBS_FILE.exists():
        _write_list(JOBS_FILE, [])


def list_properties() -> list[dict[str, Any]]:
    bootstrap_catalog()
    return _read_list(PROPERTIES_FILE)


def get_property(property_id: str) -> dict[str, Any] | None:
    return next((row for row in list_properties() if row.get("id") == property_id), None)


def save_property(payload: dict[str, Any]) -> dict[str, Any]:
    rows = list_properties()
    row = dict(payload)
    row.setdefault("id", f"prop-{uuid.uuid4().hex[:8]}")
    row["updatedAt"] = _now()
    replaced = False
    for index, existing in enumerate(rows):
        if existing.get("id") == row["id"]:
            rows[index] = {**existing, **row}
            row = rows[index]
            replaced = True
            break
    if not replaced:
        row.setdefault("createdAt", _now())
        rows.append(row)
    _write_list(PROPERTIES_FILE, rows)
    return row


def delete_property(property_id: str) -> bool:
    rows = list_properties()
    next_rows = [row for row in rows if row.get("id") != property_id]
    if len(next_rows) == len(rows):
        return False
    _write_list(PROPERTIES_FILE, next_rows)
    return True


def list_agents() -> list[dict[str, Any]]:
    bootstrap_catalog()
    return _read_list(AGENTS_FILE)


def get_agent(agent_id: str) -> dict[str, Any] | None:
    return next((row for row in list_agents() if row.get("id") == agent_id), None)


def save_agent(payload: dict[str, Any]) -> dict[str, Any]:
    rows = list_agents()
    row = dict(payload)
    row.setdefault("id", f"agent-{uuid.uuid4().hex[:8]}")
    row["updatedAt"] = _now()
    replaced = False
    for index, existing in enumerate(rows):
        if existing.get("id") == row["id"]:
            rows[index] = {**existing, **row}
            row = rows[index]
            replaced = True
            break
    if not replaced:
        row.setdefault("createdAt", _now())
        rows.append(row)
    _write_list(AGENTS_FILE, rows)
    return row


def delete_agent(agent_id: str) -> bool:
    rows = list_agents()
    next_rows = [row for row in rows if row.get("id") != agent_id]
    if len(next_rows) == len(rows):
        return False
    _write_list(AGENTS_FILE, next_rows)
    return True


def list_media() -> list[dict[str, Any]]:
    bootstrap_catalog()
    return _read_list(MEDIA_INDEX_FILE)


def get_media(media_id: str) -> dict[str, Any] | None:
    return next((row for row in list_media() if row.get("id") == media_id), None)


def add_media(
    *,
    filename: str,
    data: bytes,
    kind: str,
    property_id: str | None = None,
    agent_id: str | None = None,
    mime: str = "application/octet-stream",
) -> dict[str, Any]:
    bootstrap_catalog()
    media_id = f"media-{uuid.uuid4().hex[:10]}"
    suffix = Path(filename).suffix.lower() or ".bin"
    dest = MEDIA_UPLOADS / f"{media_id}{suffix}"
    dest.write_bytes(data)
    row = {
        "id": media_id,
        "filename": filename,
        "kind": kind,
        "path": str(dest),
        "mime": mime,
        "bytes": len(data),
        "propertyId": property_id,
        "agentId": agent_id,
        "createdAt": _now(),
    }
    rows = list_media()
    rows.append(row)
    _write_list(MEDIA_INDEX_FILE, rows)
    return row


def delete_media(media_id: str) -> bool:
    rows = list_media()
    match = next((row for row in rows if row.get("id") == media_id), None)
    if match is None:
        return False
    path = Path(str(match.get("path") or ""))
    if path.is_file():
        path.unlink()
    _write_list(MEDIA_INDEX_FILE, [row for row in rows if row.get("id") != media_id])
    _strip_media_id(media_id)
    return True


def _strip_media_id(media_id: str) -> None:
    properties = list_properties()
    props_changed = False
    for property_row in properties:
        ids = dict(property_row.get("mediaIds") or {})
        for key in ("exteriorPhotos", "interiorPhotos", "videoClips"):
            before = list(ids.get(key) or [])
            after = [item for item in before if item != media_id]
            if after != before:
                ids[key] = after
                props_changed = True
        if ids != (property_row.get("mediaIds") or {}):
            property_row["mediaIds"] = ids
    if props_changed:
        _write_list(PROPERTIES_FILE, properties)

    agents = list_agents()
    agents_changed = False
    for agent_row in agents:
        if agent_row.get("photoMediaId") == media_id:
            agent_row["photoMediaId"] = ""
            agents_changed = True
        if agent_row.get("logoMediaId") == media_id:
            agent_row["logoMediaId"] = ""
            agents_changed = True
    if agents_changed:
        _write_list(AGENTS_FILE, agents)


def list_jobs() -> list[dict[str, Any]]:
    bootstrap_catalog()
    return sorted(_read_list(JOBS_FILE), key=lambda row: row.get("updatedAt", ""), reverse=True)


def get_job(job_id: str) -> dict[str, Any] | None:
    return next((row for row in list_jobs() if row.get("id") == job_id), None)


def save_job(payload: dict[str, Any]) -> dict[str, Any]:
    rows = list_jobs()
    row = dict(payload)
    row.setdefault("id", f"job-{uuid.uuid4().hex[:8]}")
    row["updatedAt"] = _now()
    replaced = False
    for index, existing in enumerate(rows):
        if existing.get("id") == row["id"]:
            rows[index] = {**existing, **row}
            row = rows[index]
            replaced = True
            break
    if not replaced:
        row.setdefault("createdAt", _now())
        rows.append(row)
    _write_list(JOBS_FILE, rows)
    return row


def get_settings() -> dict[str, Any]:
    bootstrap_catalog()
    return _read_object(SETTINGS_FILE, {})


def save_settings(payload: dict[str, Any]) -> dict[str, Any]:
    current = get_settings()
    merged = {**current, **payload}
    _write_object(SETTINGS_FILE, merged)
    return merged


_LISTING_TEMPLATE_ORDER = [
    "just-listed",
    "property-showcase",
    "open-house",
    "just-sold",
    "price-reduced",
    "coming-soon",
    "market-update",
]

_LISTING_DEFAULTS = {
    "duration": 30,
    "fps": 30,
    "compositionId": "UPCAJustListed",
    "rendererFamily": "upca-just-listed",
    "audience": "property",
}


def _hydrate_templates(templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base = next((row for row in templates if row.get("id") == "just-listed"), None)
    hydrated: list[dict[str, Any]] = []
    for item in templates:
        row = dict(item)
        for key, value in _LISTING_DEFAULTS.items():
            row.setdefault(key, value)
        if not row.get("scenes") and base and base.get("scenes"):
            row["scenes"] = list(base["scenes"])
        if not row.get("requiredFields") and base and base.get("requiredFields"):
            row["requiredFields"] = list(base["requiredFields"])
        hydrated.append(row)
    rank = {template_id: index for index, template_id in enumerate(_LISTING_TEMPLATE_ORDER)}
    hydrated.sort(key=lambda row: (rank.get(str(row.get("id") or ""), 99), str(row.get("name") or "")))
    return hydrated


def list_templates() -> list[dict[str, Any]]:
    import yaml

    templates: list[dict[str, Any]] = []
    if TEMPLATES_DIR.exists():
        for path in sorted(TEMPLATES_DIR.glob("*.yaml")):
            with open(path, encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            if isinstance(data, dict) and data.get("id"):
                templates.append(data)
    return _hydrate_templates(templates)


def get_template(template_id: str) -> dict[str, Any] | None:
    return next((row for row in list_templates() if row.get("id") == template_id), None)
