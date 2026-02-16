import json
import os
from typing import Any, Dict, Iterable, List, Optional


def _parse_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def _release_formats(release: Dict[str, Any]) -> Iterable[str]:
    media_list = release.get("Media")
    if media_list is None:
        media_list = release.get("media")
    for medium in media_list or []:
        fmt = medium.get("Format") if isinstance(medium, dict) else None
        if fmt:
            yield str(fmt).lower()


def _has_excluded_format(release: Dict[str, Any], excluded_tokens: List[str]) -> bool:
    if not excluded_tokens:
        return False
    for fmt in _release_formats(release):
        for token in excluded_tokens:
            if token in fmt:
                return True
    return False


def after_query(results: Any, context: Dict[str, Any]) -> Any:
    if context.get("sql_file") != "release_group_by_id.sql":
        return None

    excluded_tokens = _parse_list(os.environ.get("LMBRIDGE_RELEASE_FILTER_MEDIA_EXCLUDE"))
    if not excluded_tokens:
        return None

    updated = []
    for row in results or []:
        album_json = row.get("album") if isinstance(row, dict) else None
        if not album_json:
            updated.append(row)
            continue

        try:
            album = json.loads(album_json) if isinstance(album_json, str) else album_json
        except Exception:
            updated.append(row)
            continue

        releases = album.get("Releases") if isinstance(album, dict) else None
        if releases is None and isinstance(album, dict):
            releases = album.get("releases")
        if isinstance(releases, list):
            filtered = [
                release for release in releases
                if not _has_excluded_format(release, excluded_tokens)
            ]
            if filtered:
                if "Releases" in album:
                    album["Releases"] = filtered
                else:
                    album["releases"] = filtered

        try:
            row["album"] = json.dumps(album, separators=(",", ":"))
        except Exception:
            updated.append(row)
            continue

        updated.append(row)

    return updated
