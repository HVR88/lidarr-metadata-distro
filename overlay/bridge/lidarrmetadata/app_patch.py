import os

async def safe_spotify_set(spotify_id, albumid):
    """
    Overlay helper: only set SPOTIFY_CACHE if albumid is valid
    """
    from lidarrmetadata import app as upstream_app
    from lidarrmetadata import util
    if albumid:
        await util.SPOTIFY_CACHE.set(spotify_id, albumid, ttl=upstream_app.app.config['CACHE_TTL']['cloudflare'])
    else:
        # Skip caching 0 or invalid IDs to avoid polluting the cache
        upstream_app.app.logger.debug(f"Skipping caching invalid Spotify ID: {spotify_id}")


def apply() -> None:
    """
    Apply optional runtime patches. Currently a no-op unless enabled.
    """
    from lidarrmetadata import mitm
    from lidarrmetadata import db_hooks
    if mitm.is_enabled():
        from lidarrmetadata import app as upstream_app

        @upstream_app.app.after_request
        async def _lmbridge_mitm_hook(response):
            return await mitm.apply_response(response)

    if db_hooks.is_enabled():
        from lidarrmetadata import provider as provider_mod

        original_query_from_file = provider_mod.MusicbrainzDbProvider.query_from_file
        if not getattr(original_query_from_file, "_lmbridge_sql_file_hooked", False):

            async def _lmbridge_query_from_file(self, sql_file, *args):
                token = db_hooks.set_sql_file(sql_file)
                try:
                    return await original_query_from_file(self, sql_file, *args)
                finally:
                    db_hooks.reset_sql_file(token)

            _lmbridge_query_from_file._lmbridge_sql_file_hooked = True
            provider_mod.MusicbrainzDbProvider.query_from_file = _lmbridge_query_from_file

        original = provider_mod.MusicbrainzDbProvider.map_query
        if not getattr(original, "_lmbridge_db_hooked", False):

            async def _lmbridge_map_query(self, sql, *args, _conn=None):
                context = {
                    "provider": self.__class__.__name__,
                    "sql": sql,
                    "args": args,
                    "sql_file": db_hooks.get_sql_file(),
                }

                new_sql, new_args, pool_key = db_hooks.apply_before(sql, args, context)
                context["sql"] = new_sql
                context["args"] = new_args
                context["pool_key"] = pool_key

                if pool_key and pool_key != "default":
                    pool = await db_hooks.get_pool(self, pool_key)
                    async with pool.acquire() as _alt_conn:
                        results = await original(self, new_sql, *new_args, _conn=_alt_conn)
                else:
                    results = await original(self, new_sql, *new_args, _conn=_conn)
                return db_hooks.apply_after(results, context)

            _lmbridge_map_query._lmbridge_db_hooked = True
            provider_mod.MusicbrainzDbProvider.map_query = _lmbridge_map_query

    if os.environ.get("LMBRIDGE_PATCH_SPOTIFY_CACHE", "").lower() in {"1", "true", "yes"}:
        # Placeholder: wire safe_spotify_set into call sites if/when needed.
        # Intentionally no behavior change today.
        return
