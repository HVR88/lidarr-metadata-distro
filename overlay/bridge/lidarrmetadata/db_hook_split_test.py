import logging
import os
import uuid
from typing import Any, Dict, Optional, Tuple

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


def _map_rgids(rgids, source_id: str, synth_id: str):
    if isinstance(rgids, (list, tuple)):
        mapped = [source_id if rgid == synth_id else rgid for rgid in rgids]
        return list(mapped), any(rgid == synth_id for rgid in rgids)

    mapped = source_id if rgids == synth_id else rgids
    return [mapped], rgids == synth_id


def before_query(sql: str, args: Tuple[Any, ...], context: Dict[str, Any]):
    if context.get("sql_file") != "release_group_by_id.sql":
        return None

    source_id = _get_source_id()
    synth_id = _synthetic_id()
    if not source_id or not synth_id:
        return None

    if not args:
        return None

    rgids = args[0]
    mapped_rgids, changed = _map_rgids(rgids, source_id, synth_id)
    if not changed:
        return None

    new_args = (mapped_rgids,) + tuple(args[1:])
    return sql, new_args
