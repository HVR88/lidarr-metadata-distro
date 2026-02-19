import copy
import logging
import os
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DEFAULT_NAMESPACE = "2f2bbf9f-7a9e-4d27-9b5b-1f0b3a1d5f2a"


def _get_source_id() -> Optional[str]:
    return os.environ.get("LMBRIDGE_SPLIT_TEST_SOURCE_RG_ID")


def _get_partition_key() -> str:
    return os.environ.get("LMBRIDGE_SPLIT_TEST_PARTITION_KEY", "variant_1")


def _get_namespace() -> str:
    return os.environ.get("LMBRIDGE_SPLIT_TEST_NAMESPACE", _DEFAULT_NAMESPACE)


def _synthetic_id() -> Optional[str]:
    explicit = os.environ.get("LMBRIDGE_SPLIT_TEST_SYNTH_ID")
    if explicit:
        return explicit

    source_id = _get_source_id()
    if not source_id:
        return None

    try:
        namespace = uuid.UUID(_get_namespace())
    except Exception:
        logger.warning("LM-Bridge split test: invalid namespace, skipping synthetic id")
        return None

    name = f"rg:{source_id}|part:{_get_partition_key()}"
    return str(uuid.uuid5(namespace, name))


def _ensure_old_id(payload: Dict[str, Any], old_id: str) -> None:
    old_ids = list(payload.get("OldIds") or [])
    if old_id not in old_ids:
        old_ids.append(old_id)
    payload["OldIds"] = old_ids


def _append_suffix(title: Optional[str]) -> str:
    if not title:
        return "[LMBridge Split Test]"
    if "[LMBridge Split Test]" in title:
        return title
    return f"{title} [LMBridge Split Test]"


def _inject_synthetic_album(payload: Dict[str, Any]) -> Dict[str, Any]:
    source_id = _get_source_id()
    synth_id = _synthetic_id()
    if not source_id or not synth_id:
        return payload

    albums = payload.get("Albums")
    if not isinstance(albums, list):
        return payload

    if any(album.get("Id") == synth_id for album in albums if isinstance(album, dict)):
        return payload

    source_album = next(
        (album for album in albums if isinstance(album, dict) and album.get("Id") == source_id),
        None,
    )
    if source_album is None:
        return payload

    synthetic = copy.deepcopy(source_album)
    synthetic["Id"] = synth_id
    _ensure_old_id(synthetic, source_id)
    synthetic["Title"] = _append_suffix(synthetic.get("Title"))
    albums.append(synthetic)
    return payload


def _rewrite_album_id(payload: Dict[str, Any], path: str) -> Dict[str, Any]:
    synth_id = _synthetic_id()
    source_id = _get_source_id()
    if not synth_id or not source_id:
        return payload

    if not path.rstrip("/").endswith(synth_id):
        return payload

    updated = copy.deepcopy(payload)
    updated["Id"] = synth_id
    _ensure_old_id(updated, source_id)
    updated["Title"] = _append_suffix(updated.get("Title"))
    return updated


def transform_payload(payload: Any, context: Dict[str, Any]) -> Any:
    path = context.get("path", "")

    if isinstance(payload, dict) and path.startswith("/artist/"):
        return _inject_synthetic_album(payload)

    if isinstance(payload, dict) and path.startswith("/album/"):
        return _rewrite_album_id(payload, path)

    return payload
