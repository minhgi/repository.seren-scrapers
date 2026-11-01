# -*- coding: utf-8 -*-
#
# AIOStreams (personal manifest) - direct provider. Disabled until the user turns on
# "AIOStreams Scraper" and enters their manifest URL in Seren's Advanced settings
# (aiostreams.* next to the MediaFusion settings). Named aiostreams_manifest because
# Seren's provider table is unique on provider name and torrent/aiostreams.py exists.

from providerModules.a4kScrapers import aiostreams_manifest as _aio


class sources(object):
    def movie(self, title, year, imdb=None, simple_info=None, info=None, **kwargs):
        if not _aio.is_enabled():
            return []
        meta = (info or {}).get("info", {})
        return _aio.AIOStreamsScraper().movie(imdb or meta.get("imdb_id"), meta.get("tmdb_id"))

    def episode(self, simple_info, info, **kwargs):
        if not _aio.is_enabled():
            return []
        meta = (info or {}).get("info", {})
        imdb = meta.get("tvshow.imdb_id")
        tmdb = meta.get("tvshow.tmdb_id") or meta.get("tmdb_show_id")
        season = (simple_info or {}).get("season_number") or meta.get("season")
        episode = (simple_info or {}).get("episode_number") or meta.get("episode")
        return _aio.AIOStreamsScraper().episode(imdb, tmdb, season, episode)
