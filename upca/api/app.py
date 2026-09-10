"""UPCA dashboard API — separate process from Backlot (:4760)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from lib.paths import PROJECTS_DIR
from upca.paths import MEDIA_UPLOADS, ensure_runtime_dirs
from upca.services import catalog
from upca.services import job_runner

app = FastAPI(title="UPCA Video Factory", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PropertyIn(BaseModel):
    id: str | None = None
    address: str
    city: str
    province: str = ""
    postalCode: str = ""
    price: str | int | float
    bedrooms: int | float | str = ""
    bathrooms: int | float | str = ""
    squareFeet: int | float | str = ""
    propertyType: str = ""
    description: str = ""
    features: list[str] = []
    mediaIds: dict = {}


class AgentIn(BaseModel):
    id: str | None = None
    name: str
    photoMediaId: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    brokerage: str = ""
    logoMediaId: str = ""
    socialLinks: dict = {}


class JobIn(BaseModel):
    propertyId: str
    agentId: str
    templateId: str = "just-listed"
    format: str = "9:16"


class SettingsIn(BaseModel):
    branding: dict | None = None
    cta: dict | None = None
    defaultFormat: str | None = None
    defaultFps: int | None = None
    voiceoverEnabled: bool | None = None


@app.on_event("startup")
def _startup() -> None:
    from lib.ffmpeg_bins import ensure_on_path

    ensure_runtime_dirs()
    catalog.bootstrap_catalog()
    ensure_on_path()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "app": "upca"}


@app.get("/api/properties")
def properties() -> list[dict]:
    return catalog.list_properties()


@app.post("/api/properties")
def create_property(payload: PropertyIn) -> dict:
    return catalog.save_property(payload.model_dump(exclude_none=True))


@app.get("/api/properties/{property_id}")
def property_detail(property_id: str) -> dict:
    row = catalog.get_property(property_id)
    if not row:
        raise HTTPException(404, "Property not found")
    return row


@app.put("/api/properties/{property_id}")
def update_property(property_id: str, payload: PropertyIn) -> dict:
    data = payload.model_dump(exclude_none=True)
    data["id"] = property_id
    return catalog.save_property(data)


@app.delete("/api/properties/{property_id}")
def remove_property(property_id: str) -> dict:
    if not catalog.delete_property(property_id):
        raise HTTPException(404, "Property not found")
    return {"ok": True}


@app.get("/api/agents")
def agents() -> list[dict]:
    return catalog.list_agents()


@app.post("/api/agents")
def create_agent(payload: AgentIn) -> dict:
    return catalog.save_agent(payload.model_dump(exclude_none=True))


@app.put("/api/agents/{agent_id}")
def update_agent(agent_id: str, payload: AgentIn) -> dict:
    data = payload.model_dump(exclude_none=True)
    data["id"] = agent_id
    return catalog.save_agent(data)


@app.delete("/api/agents/{agent_id}")
def remove_agent(agent_id: str) -> dict:
    if not catalog.delete_agent(agent_id):
        raise HTTPException(404, "Agent not found")
    return {"ok": True}


@app.get("/api/templates")
def templates() -> list[dict]:
    return catalog.list_templates()


@app.get("/api/media")
def media_list() -> list[dict]:
    return catalog.list_media()


@app.post("/api/media")
async def upload_media(
    request: Request,
    kind: str = Query("other"),
    filename: str = Query("upload.bin"),
    propertyId: str | None = Query(None),
    agentId: str | None = Query(None),
) -> dict:
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm"}
    suffix = Path(filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, f"Unsupported file type {suffix}")
    data = await request.body()
    if len(data) > 40 * 1024 * 1024:
        raise HTTPException(400, "File too large (40MB max)")
    return catalog.add_media(
        filename=filename or f"upload{suffix}",
        data=data,
        kind=kind,
        property_id=propertyId,
        agent_id=agentId,
        mime=request.headers.get("content-type") or "application/octet-stream",
    )


@app.get("/api/media/{media_id}/file")
def media_file(media_id: str) -> FileResponse:
    row = catalog.get_media(media_id)
    if not row:
        raise HTTPException(404, "Media not found")
    path = Path(row["path"]).resolve()
    uploads = MEDIA_UPLOADS.resolve()
    if uploads not in path.parents and path != uploads:
        raise HTTPException(403, "Path is outside the media library")
    if not path.is_file():
        raise HTTPException(404, "File missing")
    return FileResponse(path)


@app.delete("/api/media/{media_id}")
def remove_media(media_id: str) -> dict:
    if not catalog.delete_media(media_id):
        raise HTTPException(404, "Media not found")
    return {"ok": True}


@app.get("/api/jobs")
def jobs() -> list[dict]:
    return catalog.list_jobs()


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str) -> dict:
    row = catalog.get_job(job_id)
    if not row:
        raise HTTPException(404, "Job not found")
    return row


@app.post("/api/jobs")
def create_job(payload: JobIn) -> dict:
    try:
        return job_runner.create_job(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/jobs/{job_id}/prepare")
def prepare_job(job_id: str) -> dict:
    try:
        return job_runner.prepare_job(job_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@app.post("/api/jobs/{job_id}/render")
def render_job(job_id: str) -> dict:
    try:
        return job_runner.start_render_async(job_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/projects")
def projects() -> list[dict]:
    rows = []
    if PROJECTS_DIR.exists():
        for path in sorted(PROJECTS_DIR.iterdir()):
            marker = path / "project.json"
            if marker.is_file():
                import json

                with open(marker, encoding="utf-8") as handle:
                    data = json.load(handle)
                if str(data.get("pipeline_type")) == "upca-real-estate" or str(data.get("project_id", "")).startswith("upca-"):
                    rows.append(data)
    return rows


@app.get("/api/renders")
def renders() -> list[dict]:
    items = []
    for job in catalog.list_jobs():
        output = job.get("outputPath")
        if output and Path(output).is_file():
            items.append(
                {
                    "jobId": job["id"],
                    "projectId": job.get("projectId"),
                    "title": job.get("title"),
                    "format": job.get("format"),
                    "status": job.get("status"),
                    "path": output,
                }
            )
    return items


@app.get("/api/renders/{job_id}/file")
def render_file(job_id: str) -> FileResponse:
    job = catalog.get_job(job_id)
    if not job or not job.get("outputPath"):
        raise HTTPException(404, "Render not found")
    path = Path(job["outputPath"]).resolve()
    root = PROJECTS_DIR.resolve()
    if root not in path.parents and path != root:
        raise HTTPException(403, "Path is outside projects/")
    if not path.is_file():
        raise HTTPException(404, "File missing")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@app.get("/api/settings")
def settings() -> dict:
    return catalog.get_settings()


@app.put("/api/settings")
def update_settings(payload: SettingsIn) -> dict:
    data = {key: value for key, value in payload.model_dump().items() if value is not None}
    return catalog.save_settings(data)
