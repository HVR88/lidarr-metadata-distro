import importlib
import importlib.util
import logging
import os
from typing import Any, Callable, Dict, Optional, Tuple

import asyncio
import asyncpg
import contextvars

logger = logging.getLogger(__name__)

_BEFORE: Optional[Callable[[str, Tuple[Any, ...], Dict[str, Any]], Tuple[str, Tuple[Any, ...]]]] = None
_AFTER: Optional[Callable[[Any, Dict[str, Any]], Any]] = None
_LOAD_ATTEMPTED = False
_SQL_FILE = contextvars.ContextVar("lmbridge_sql_file", default=None)


def is_enabled() -> bool:
    return bool(os.environ.get("LMBRIDGE_DB_HOOK_MODULE") or os.environ.get("LMBRIDGE_DB_HOOK_PATH"))


def _load_hooks() -> None:
    global _BEFORE, _AFTER, _LOAD_ATTEMPTED
    if _LOAD_ATTEMPTED:
        return
    _LOAD_ATTEMPTED = True

    module_name = os.environ.get("LMBRIDGE_DB_HOOK_MODULE")
    file_path = os.environ.get("LMBRIDGE_DB_HOOK_PATH")

    module = None
    if module_name:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            logger.exception("LM-Bridge DB hooks: failed to import module %s", module_name)
            return

    elif file_path:
        try:
            spec = importlib.util.spec_from_file_location("lmbridge_db_hooks", file_path)
            if spec is None or spec.loader is None:
                logger.error("LM-Bridge DB hooks: cannot load hook file %s", file_path)
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception:
            logger.exception("LM-Bridge DB hooks: failed to load hook file %s", file_path)
            return

    if module is None:
        return

    before = getattr(module, "before_query", None)
    after = getattr(module, "after_query", None)

    if callable(before):
        _BEFORE = before
    if callable(after):
        _AFTER = after

    if _BEFORE is None and _AFTER is None:
        logger.error(
            "LM-Bridge DB hooks: module must define before_query(sql, args, context) or "
            "after_query(results, context)"
        )


def set_sql_file(sql_file: Optional[str]):
    return _SQL_FILE.set(sql_file)


def reset_sql_file(token) -> None:
    _SQL_FILE.reset(token)


def get_sql_file() -> Optional[str]:
    return _SQL_FILE.get()


def apply_before(
    sql: str, args: Tuple[Any, ...], context: Dict[str, Any]
) -> Tuple[str, Tuple[Any, ...], str]:
    if not is_enabled():
        return sql, args, "default"
    _load_hooks()
    if _BEFORE is None:
        return sql, args, "default"

    try:
        result = _BEFORE(sql, args, context)
    except Exception:
        logger.exception("LM-Bridge DB hooks: before_query failed")
        return sql, args, "default"

    if result is None:
        return sql, args, "default"

    try:
        new_sql, new_args, *rest = result
    except Exception:
        logger.error("LM-Bridge DB hooks: before_query must return (sql, args) or None")
        return sql, args, "default"

    if not isinstance(new_args, tuple):
        new_args = tuple(new_args)

    pool_key = "default"
    if rest:
        extra = rest[0]
        if isinstance(extra, str):
            pool_key = extra
        elif isinstance(extra, dict):
            pool_key = str(extra.get("pool", "default"))

    return new_sql, new_args, pool_key


def apply_after(results: Any, context: Dict[str, Any]) -> Any:
    if not is_enabled():
        return results
    _load_hooks()
    if _AFTER is None:
        return results

    try:
        updated = _AFTER(results, context)
    except Exception:
        logger.exception("LM-Bridge DB hooks: after_query failed")
        return results

    return results if updated is None else updated


def _pool_env(pool_key: str, suffix: str) -> Optional[str]:
    key = pool_key.upper()
    return os.environ.get(f"LMBRIDGE_DB_POOL_{key}_{suffix}")


async def get_pool(provider, pool_key: str):
    if pool_key == "default":
        return await provider._get_pool()

    pools = getattr(provider, "_lmbridge_pools", None)
    if pools is None:
        pools = {}
        provider._lmbridge_pools = pools

    locks = getattr(provider, "_lmbridge_pool_locks", None)
    if locks is None:
        locks = {}
        provider._lmbridge_pool_locks = locks

    if pool_key in pools:
        return pools[pool_key]

    lock = locks.get(pool_key)
    if lock is None:
        lock = asyncio.Lock()
        locks[pool_key] = lock

    async with lock:
        if pool_key in pools:
            return pools[pool_key]

        host = _pool_env(pool_key, "HOST")
        port = _pool_env(pool_key, "PORT")
        user = _pool_env(pool_key, "USER")
        password = _pool_env(pool_key, "PASSWORD")
        db_name = _pool_env(pool_key, "DB_NAME")

        if not host or not db_name:
            logger.error(
                "LM-Bridge DB hooks: pool %s missing HOST or DB_NAME; falling back to default",
                pool_key,
            )
            return await provider._get_pool()

        try:
            port_value = int(port) if port else provider._db_port
            pool = await asyncpg.create_pool(
                host=host,
                port=port_value,
                user=user or provider._db_user,
                password=password or provider._db_password,
                database=db_name,
                init=provider.uuid_as_str,
                statement_cache_size=0,
            )
        except Exception:
            logger.exception("LM-Bridge DB hooks: failed to create pool %s", pool_key)
            return await provider._get_pool()

        pools[pool_key] = pool
        return pool
