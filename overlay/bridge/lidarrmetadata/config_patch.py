import json
import os
from pathlib import Path
from typing import Any, Dict

from quart import jsonify, request

from lidarrmetadata import app as upstream_app
from lidarrmetadata import release_filters
from lidarrmetadata import root_patch

_STATE_DIR = Path(os.environ.get("LMBRIDGE_INIT_STATE_DIR", "/metadata/init-state"))
_STATE_FILE = Path(
    os.environ.get(
        "LMBRIDGE_RELEASE_FILTER_STATE_FILE",
        str(_STATE_DIR / "release-filter.json"),
    )
)


def register_config_routes() -> None:
    for rule in upstream_app.app.url_map.iter_rules():
        if rule.rule == "/config/release-filter":
            return

    _load_persisted_config()

    @upstream_app.app.route("/config/release-filter", methods=["POST"])
    async def _lmbridge_release_filter_config():
        payload = await request.get_json(silent=True) or {}
        enabled = _is_truthy(payload.get("enabled", True))
        exclude = payload.get("exclude_media_formats")
        if exclude is None:
            exclude = payload.get("excludeMediaFormats")
        if exclude is None:
            exclude = payload.get("media_exclude")
        include = payload.get("include_media_formats")
        if include is None:
            include = payload.get("includeMediaFormats")
        if include is None:
            include = payload.get("media_include")
        keep_only_count = payload.get("keep_only_media_count")
        if keep_only_count is None:
            keep_only_count = payload.get("keepOnlyMediaCount")
        prefer = payload.get("prefer")
        if not enabled:
            exclude = []
            include = []
            keep_only_count = None
            prefer = None

        release_filters.set_runtime_media_exclude(exclude)
        release_filters.set_runtime_media_include(include)
        release_filters.set_runtime_media_keep_only(keep_only_count)
        release_filters.set_runtime_media_prefer(prefer)
        _persist_config(
            {
                "enabled": bool(enabled),
                "exclude_media_formats": release_filters.get_runtime_media_exclude() or [],
                "include_media_formats": release_filters.get_runtime_media_include() or [],
                "keep_only_media_count": release_filters.get_runtime_media_keep_only(),
                "prefer": release_filters.get_runtime_media_prefer(),
                "lidarr_version": _extract_lidarr_version(payload),
            }
        )
        return jsonify(
            {
                "ok": True,
                "enabled": bool(enabled),
                "exclude_media_formats": release_filters.get_runtime_media_exclude() or [],
                "include_media_formats": release_filters.get_runtime_media_include() or [],
                "keep_only_media_count": release_filters.get_runtime_media_keep_only(),
                "prefer": release_filters.get_runtime_media_prefer(),
            }
        )


def _is_truthy(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _extract_lidarr_version(payload: Dict[str, Any]) -> str:
    value = payload.get("lidarr_version")
    if value is None:
        value = payload.get("lidarrVersion")
    if value is None:
        value = payload.get("lidarr_version_string")
    if value is None:
        value = payload.get("lidarrVersionString")
    return str(value).strip() if value else ""


def _load_persisted_config() -> None:
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return

    enabled = bool(data.get("enabled", True))
    exclude = data.get("exclude_media_formats") or []
    include = data.get("include_media_formats") or []
    keep_only_count = data.get("keep_only_media_count")
    prefer = data.get("prefer")
    if not enabled:
        exclude = []
        include = []
        keep_only_count = None
        prefer = None

    release_filters.set_runtime_media_exclude(exclude)
    release_filters.set_runtime_media_include(include)
    release_filters.set_runtime_media_keep_only(keep_only_count)
    release_filters.set_runtime_media_prefer(prefer)

    lidarr_version = (data.get("lidarr_version") or "").strip()
    if lidarr_version:
        root_patch.set_lidarr_version(lidarr_version)


def _persist_config(data: Dict[str, Any]) -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "enabled": bool(data.get("enabled", True)),
            "exclude_media_formats": data.get("exclude_media_formats") or [],
            "include_media_formats": data.get("include_media_formats") or [],
            "keep_only_media_count": data.get("keep_only_media_count"),
            "prefer": data.get("prefer"),
        }
        lidarr_version = (data.get("lidarr_version") or "").strip()
        if lidarr_version:
            payload["lidarr_version"] = lidarr_version
            root_patch.set_lidarr_version(lidarr_version)
        _STATE_FILE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        return
