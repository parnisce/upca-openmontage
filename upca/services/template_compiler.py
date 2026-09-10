"""Compile a UPCA template + catalog records into OpenMontage artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from upca.paths import FORMAT_PROFILES, FORMAT_RESOLUTIONS
from upca.services.catalog import get_media


def format_price(value: Any) -> str:
    raw = str(value).replace("$", "").replace(",", "").strip()
    try:
        number = float(raw)
        if number.is_integer():
            return f"${int(number):,}"
        return f"${number:,.2f}"
    except ValueError:
        return str(value)


def _media_path(media_id: str | None) -> str:
    if not media_id:
        return ""
    record = get_media(media_id)
    if not record:
        return ""
    path = Path(str(record.get("path") or ""))
    return str(path) if path.is_file() else ""


def resolve_media_ids(ids: list[str] | None) -> list[str]:
    paths: list[str] = []
    for media_id in ids or []:
        path = _media_path(media_id)
        if path:
            paths.append(path)
    return paths


def build_package(
    *,
    template: dict[str, Any],
    property_row: dict[str, Any],
    agent_row: dict[str, Any],
    settings: dict[str, Any],
    format_name: str,
    project_media: dict[str, list[str] | str],
) -> dict[str, Any]:
    branding = dict(settings.get("branding") or {})
    default_cta = dict(settings.get("cta") or {})
    media_ids = property_row.get("mediaIds") or {}
    return {
        "version": "1.0",
        "templateId": template["id"],
        "property": {
            "address": property_row.get("address", ""),
            "city": property_row.get("city", ""),
            "province": property_row.get("province", ""),
            "postalCode": property_row.get("postalCode", ""),
            "price": format_price(property_row.get("price", "")),
            "bedrooms": property_row.get("bedrooms", ""),
            "bathrooms": property_row.get("bathrooms", ""),
            "squareFeet": property_row.get("squareFeet", ""),
            "propertyType": property_row.get("propertyType", ""),
            "description": property_row.get("description", ""),
            "features": list(property_row.get("features") or []),
        },
        "agent": {
            "name": agent_row.get("name", ""),
            "photo": project_media.get("agentPhoto") or _media_path(agent_row.get("photoMediaId")),
            "phone": agent_row.get("phone", ""),
            "email": agent_row.get("email", ""),
            "website": agent_row.get("website", ""),
            "brokerage": agent_row.get("brokerage", ""),
            "socialLinks": dict(agent_row.get("socialLinks") or {}),
        },
        "media": {
            "exteriorPhotos": list(project_media.get("exteriorPhotos") or resolve_media_ids(media_ids.get("exteriorPhotos"))),
            "interiorPhotos": list(project_media.get("interiorPhotos") or resolve_media_ids(media_ids.get("interiorPhotos"))),
            "videoClips": list(project_media.get("videoClips") or resolve_media_ids(media_ids.get("videoClips"))),
            "agentPhoto": project_media.get("agentPhoto") or _media_path(agent_row.get("photoMediaId")),
            "agentLogo": project_media.get("agentLogo") or _media_path(agent_row.get("logoMediaId")),
        },
        "branding": {
            "logo": branding.get("logo", ""),
            "primaryColor": branding.get("primaryColor", "#C4A35A"),
            "secondaryColor": branding.get("secondaryColor", "#0F1C24"),
            "fonts": dict(branding.get("fonts") or {"heading": "Cormorant Garamond", "body": "Inter"}),
        },
        "video": {
            "duration": int(template.get("duration") or 30),
            "format": format_name,
            "resolution": FORMAT_RESOLUTIONS[format_name],
            "fps": int(settings.get("defaultFps") or template.get("fps") or 30),
        },
        "copy": {
            "headline": template.get("headline") or "JUST LISTED",
            "livingLabel": template.get("livingLabel") or "INTERIORS",
            "roomsLabel": template.get("roomsLabel") or "PRIVATE ROOMS",
            "statsKicker": template.get("statsKicker") or "LISTED AT",
            "locationKicker": template.get("locationKicker") or "LOCATION",
        },
        "cta": {
            "text": template.get("ctaText") or default_cta.get("text") or "BOOK A SHOWING",
            "phone": default_cta.get("phone") or agent_row.get("phone", ""),
            "website": default_cta.get("website") or agent_row.get("website", ""),
        },
        "voiceoverEnabled": bool(settings.get("voiceoverEnabled")),
    }


def build_brief(package: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    prop = package["property"]
    fmt = package["video"]["format"]
    platform = {"9:16": "instagram", "16:9": "linkedin", "1:1": "generic"}[fmt]
    return {
        "version": "1.0",
        "title": f"{template.get('headline', 'JUST LISTED')} — {prop['address']}",
        "hook": template.get("headline", "JUST LISTED"),
        "key_points": [
            str(prop.get("price") or ""),
            f"{prop.get('bedrooms')} bedrooms",
            f"{prop.get('bathrooms')} bathrooms",
            f"{prop.get('city')}, {prop.get('province')}",
        ],
        "core_message": prop.get("description") or f"New listing at {prop['address']}",
        "cta": package["cta"]["text"],
        "tone": "elevated residential",
        "style": "upca-brand",
        "target_audience": "home buyers and local agents",
        "target_platform": platform,
        "target_duration_seconds": package["video"]["duration"],
        "metadata": {"templateId": template["id"], "format": fmt},
    }


def build_script(package: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    prop = package["property"]
    agent = package["agent"]
    city_line = f"{prop['city']}, {prop['province']}".strip(", ")
    sections = [
        {
            "id": "sc1",
            "label": "Hero",
            "text": f"{template.get('headline', 'JUST LISTED')}. {prop['address']}.",
            "start_seconds": 0,
            "end_seconds": 3,
            "speaker_directions": "Warm, confident, no rush",
            "delivery_cues": {"pace": "measured", "energy": "assured"},
        },
        {
            "id": "sc2",
            "label": "Address",
            "text": f"{prop['address']}, {city_line}.",
            "start_seconds": 3,
            "end_seconds": 8,
            "delivery_cues": {"pace": "conversational"},
        },
        {
            "id": "sc3",
            "label": "Interior",
            "text": "Step inside the living spaces.",
            "start_seconds": 8,
            "end_seconds": 13,
            "delivery_cues": {"pace": "measured"},
        },
        {
            "id": "sc4",
            "label": "Rooms",
            "text": f"{prop.get('bedrooms')} bedrooms. {prop.get('bathrooms')} bathrooms.",
            "start_seconds": 13,
            "end_seconds": 18,
            "delivery_cues": {"pace": "measured"},
        },
        {
            "id": "sc5",
            "label": "Stats",
            "text": f"{template.get('statsKicker', 'LISTED AT')}. {prop.get('price')}. {prop.get('squareFeet')} square feet.",
            "start_seconds": 18,
            "end_seconds": 23,
            "delivery_cues": {"pace": "measured", "emphasis_words": [str(prop.get("price") or "")]},
        },
        {
            "id": "sc6",
            "label": "Location",
            "text": f"Discover {prop['city']}.",
            "start_seconds": 23,
            "end_seconds": 27,
            "delivery_cues": {"pace": "conversational"},
        },
        {
            "id": "sc7",
            "label": "CTA",
            "text": f"{package['cta']['text']} with {agent.get('name') or 'your UPCA advisor'}.",
            "start_seconds": 27,
            "end_seconds": 30,
            "delivery_cues": {"pace": "measured", "energy": "inviting"},
        },
    ]
    return {
        "version": "1.0",
        "title": f"{template.get('name')} — {prop['address']}",
        "total_duration_seconds": package["video"]["duration"],
        "voice_performance": {
            "performance_intent": "Invite a showing without sounding like a discount ad",
            "pacing_profile": "conversational",
            "energy_curve": "open strong, settle, close with a clear ask",
            "pause_policy": "Breath after the price",
            "sample_section_id": "sc5",
        },
        "sections": sections,
    }


def _photo_for_scene(package: dict[str, Any], kind: str) -> str:
    media = package.get("media") or {}
    if kind == "agent":
        return str(media.get("agentPhoto") or "")
    if kind == "interior":
        interiors = list(media.get("interiorPhotos") or [])
        exteriors = list(media.get("exteriorPhotos") or [])
        return interiors[0] if interiors else (exteriors[0] if exteriors else "")
    exteriors = list(media.get("exteriorPhotos") or [])
    interiors = list(media.get("interiorPhotos") or [])
    return exteriors[0] if exteriors else (interiors[0] if interiors else "")


def build_scene_plan(package: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    scenes: list[dict[str, Any]] = []
    for beat in template.get("scenes") or []:
        kind = str(beat.get("photoKind") or "exterior")
        source = _photo_for_scene(package, kind)
        scenes.append(
            {
                "id": beat["id"],
                "type": beat["type"],
                "description": beat.get("label") or beat["id"],
                "start_seconds": beat["start"],
                "end_seconds": beat["end"],
                "script_section_id": beat["id"],
                "shot_intent": beat.get("shot_intent", ""),
                "narrative_role": beat.get("narrative_role", "establish_context"),
                "information_role": beat.get("information_role", ""),
                "hero_moment": bool(beat.get("hero_moment")),
                "shot_language": {
                    "shot_size": beat.get("shot_size", "wide"),
                    "camera_movement": beat.get("camera_movement", "static"),
                    "lighting_key": "natural",
                    "depth_of_field": "medium",
                    "color_temperature": "warm",
                },
                "required_assets": [
                    {
                        "type": "image",
                        "description": f"{kind} still for {beat['id']}",
                        "source": "provided",
                    }
                ],
                "overlay_notes": source,
            }
        )
    return {
        "version": "1.0",
        "style_playbook": "upca-brand",
        "scenes": scenes,
        "metadata": {"templateId": template["id"]},
    }


def build_asset_manifest(package: dict[str, Any], copied: dict[str, str]) -> dict[str, Any]:
    """copied maps original/absolute path → project-relative path."""
    assets: list[dict[str, Any]] = []
    media = package.get("media") or {}
    scene_kinds = {
        "exterior": "sc2",
        "interior": "sc3",
        "agent": "sc7",
        "logo": "sc7",
        "video": "sc2",
    }

    def add(path: str, asset_type: str, scene_id: str, subtype: str) -> None:
        if not path:
            return
        rel = copied.get(path, path)
        assets.append(
            {
                "id": f"asset_{len(assets) + 1:02d}",
                "type": asset_type,
                "path": rel.replace("\\", "/"),
                "source_tool": "provided",
                "scene_id": scene_id,
                "subtype": subtype,
                "generation_summary": "Operator-provided UPCA media",
                "provider": "upca_library",
            }
        )

    for path in media.get("exteriorPhotos") or []:
        add(str(path), "image", scene_kinds["exterior"], "exterior")
    for path in media.get("interiorPhotos") or []:
        add(str(path), "image", scene_kinds["interior"], "interior")
    for path in media.get("videoClips") or []:
        add(str(path), "video", scene_kinds["video"], "listing_clip")
    add(str(media.get("agentPhoto") or ""), "image", scene_kinds["agent"], "agent_photo")
    add(str(media.get("agentLogo") or ""), "image", scene_kinds["logo"], "agent_logo")
    return {"version": "1.0", "assets": assets, "total_cost_usd": 0}


def build_edit_decisions(
    package: dict[str, Any],
    template: dict[str, Any],
    asset_manifest: dict[str, Any],
) -> dict[str, Any]:
    by_scene: dict[str, str] = {}
    for asset in asset_manifest.get("assets") or []:
        by_scene.setdefault(asset["scene_id"], asset["id"])
    fallback = next((asset["id"] for asset in asset_manifest.get("assets") or []), "")
    cuts = []
    for beat in template.get("scenes") or []:
        source = by_scene.get(beat["id"]) or fallback or ""
        cuts.append(
            {
                "id": beat["id"],
                "source": source,
                "in_seconds": float(beat["start"]),
                "out_seconds": float(beat["end"]),
                "layer": "primary",
                "transform": {
                    "animation": "ken-burns-slow-zoom"
                    if beat.get("camera_movement") != "static"
                    else "static"
                },
                "transition_in": "fade",
                "transition_out": "fade",
                "transition_duration": 0.4,
                "reason": beat.get("label") or beat["id"],
            }
        )
    return {
        "version": "1.0",
        "cuts": cuts,
        "render_runtime": "remotion",
        "renderer_family": template.get("rendererFamily", "upca-just-listed"),
        "composition_mode": "templated",
        "overlays": [],
        "metadata": {
            "upca": package,
            "playbook": "upca-brand",
            "profile": FORMAT_PROFILES[package["video"]["format"]],
            "voiceover": "skipped" if not package.get("voiceoverEnabled") else "required",
            "target_duration_seconds": package["video"]["duration"],
        },
    }


def build_publish_log(package: dict[str, Any], output_path: str) -> dict[str, Any]:
    return {
        "version": "1.0",
        "entries": [
            {
                "platform": "local",
                "status": "exported",
                "export_path": output_path,
                "visibility": "private",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata_used": {
                    "title": f"{package['property']['address']} — {package.get('copy', {}).get('headline', 'JUST LISTED')}",
                    "description": package["property"].get("description", ""),
                    "hashtags": [str(package.get("copy", {}).get("headline") or "JustListed").replace(" ", ""), "UPCA"],
                },
            }
        ],
    }
