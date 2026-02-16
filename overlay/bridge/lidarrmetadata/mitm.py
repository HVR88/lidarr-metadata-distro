import importlib
import importlib.util
import json
import logging
import os
from typing import Any, Callable, Dict, Optional

from quart import request

logger = logging.getLogger(__name__)

_TRANSFORM: Optional[Callable[[Any, Dict[str, Any]], Any]] = None
_LOAD_ATTEMPTED = False


def is_enabled() -> bool:
    return bool(os.environ.get("LMBRIDGE_MITM_MODULE") or os.environ.get("LMBRIDGE_MITM_PATH"))


def _load_transform() -> Optional[Callable[[Any, Dict[str, Any]], Any]]:
    global _TRANSFORM, _LOAD_ATTEMPTED
    if _LOAD_ATTEMPTED:
        return _TRANSFORM
    _LOAD_ATTEMPTED = True

    module_name = os.environ.get("LMBRIDGE_MITM_MODULE")
    file_path = os.environ.get("LMBRIDGE_MITM_PATH")

    if module_name:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            logger.exception("LM-Bridge MITM: failed to import module %s", module_name)
            return None

        transform = getattr(module, "transform_payload", None)
        if callable(transform):
            _TRANSFORM = transform
            return _TRANSFORM
        logger.error("LM-Bridge MITM: module %s missing transform_payload(payload, context)", module_name)
        return None

    if file_path:
        try:
            spec = importlib.util.spec_from_file_location("lmbridge_mitm_hook", file_path)
            if spec is None or spec.loader is None:
                logger.error("LM-Bridge MITM: cannot load hook file %s", file_path)
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception:
            logger.exception("LM-Bridge MITM: failed to load hook file %s", file_path)
            return None

        transform = getattr(module, "transform_payload", None)
        if callable(transform):
            _TRANSFORM = transform
            return _TRANSFORM
        logger.error("LM-Bridge MITM: hook file %s missing transform_payload(payload, context)", file_path)
        return None

    return None


async def apply_response(response):
    if not is_enabled():
        return response

    transform = _load_transform()
    if not transform:
        return response

    content_type = response.content_type or ""
    if "application/json" not in content_type:
        return response

    try:
        raw = await response.get_data()
    except Exception:
        logger.exception("LM-Bridge MITM: failed reading response body")
        return response

    if not raw:
        return response

    try:
        payload = json.loads(raw)
    except Exception:
        return response

    context = {
        "path": request.path,
        "method": request.method,
        "query": dict(request.args),
        "headers": {k: v for k, v in request.headers.items()},
    }

    try:
        new_payload = transform(payload, context)
    except Exception:
        logger.exception("LM-Bridge MITM: transform_payload failed")
        return response

    if new_payload is None or new_payload is payload:
        return response

    try:
        response.set_data(json.dumps(new_payload, separators=(",", ":")))
    except Exception:
        logger.exception("LM-Bridge MITM: failed to update response body")
        return response

    return response
