# -*- coding: utf-8 -*-
"""
AIOStreams (personal manifest) scraper for Seren, shipped inside a4kScrapers.

Queries the user's own AIOStreams instance through their manifest URL and hands
the results to Seren as 'direct' sources. AIOStreams does the searching,
filtering and sorting; Seren only plays the link.

Adapted from djdirty60/seren-aiostreams-provider v1.0.1 (commit a55ded4,
https://github.com/djdirty60/seren-aiostreams-provider). The upstream project
states no license. Changes here: settings are read from Seren's own settings
(aiostreams.* - Advanced tab, next to the MediaFusion settings) instead of a
provider-package settings table.

Separate from the anonymous demo-endpoint scraper in en/torrent/aiostreams.py,
which is a torrent scraper and needs no account.
"""
import json
import re

try:  # Python 3
    from urllib.parse import quote, urlencode
except ImportError:  # pragma: no cover
    from urllib import quote, urlencode

import requests

USER_AGENT = "AIOStreams-Seren/1.0"  # 'AIO...' => AIOStreams stuurt extra streamData mee

SKIP_TYPES = {"error", "statistic", "info", "external", "youtube", "p2p", "live"}

VISUAL_MAP = {
    "DV": {"DV"},
    "DV ONLY": {"DV"},
    "HDR+DV": {"DV", "HDR"},
    "HDR": {"HDR"},
    "HDR10": {"HDR"},
    "HDR10+": {"HDR"},
    "HDR ONLY": {"HDR"},
    "HLG": {"HDR"},
    "SDR": {"SDR"},
    "3D": {"3D"},
}
AUDIO_MAP = {
    "ATMOS": "ATMOS",
    "TRUEHD": "TRUEHD",
    "DTS:X": "DTS-X",
    "DTS-HD MA": "DTS-HDMA",
    "DTS-HD": "DTS-HD",
    "DTS-ES": "DTS",
    "DTS": "DTS",
    "DD+": "DD+",
    "DD": "DD",
    "AAC": "AAC",
    "OPUS": "OPUS",
}
ENCODE_MAP = {"HEVC": "HEVC", "AVC": "AVC", "AV1": "AV1", "XVID": "XVID", "DIVX": "DIVX"}
QUALITY_MAP = {
    "BLURAY REMUX": {"REMUX", "BLURAY"},
    "BLURAY": {"BLURAY"},
    "WEB-DL": {"WEB"},
    "WEBRIP": {"WEB"},
    "HDTV": {"HDTV"},
    "CAM": {"CAM"},
    "TS": {"CAM"},
    "TC": {"CAM"},
    "SCR": {"SCR"},
    "DVDRIP": {"DVDRIP"},
    "HDRIP": {"HD-RIP"},
}
RESOLUTION_MAP = {"2160p": "4K", "1440p": "1080p", "1080p": "1080p", "720p": "720p"}


def _seren_setting(name):
    """Raw string value of a Seren setting (same idiom as torrent/aiostreams.py's mf.token)."""
    try:
        import xbmcaddon

        return (xbmcaddon.Addon("plugin.video.seren").getSetting(name) or "").strip()
    except Exception:
        return ""


def _bool_setting(name, default):
    value = _seren_setting(name).lower()
    if value == "true":
        return True
    if value == "false":
        return False
    return default


def is_enabled():
    return _bool_setting("aiostreams.enabled", False)


def _log(msg, level="info"):
    try:
        from resources.lib.modules.globals import g

        g.log("[AIOStreams] {}".format(msg), level)
    except Exception:
        pass


def base_url_from_manifest(url):
    """Turns a (manifest) URL into the add-on base URL."""
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("stremio://"):
        url = "https://" + url[len("stremio://"):]
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    url = url.split("?")[0].rstrip("/")
    if url.endswith("/manifest.json"):
        url = url[: -len("/manifest.json")]
    elif url.endswith("/configure"):
        url = url[: -len("/configure")]
    return url.rstrip("/")


def _fallback_info(title):
    try:
        from resources.lib.common import source_utils

        return set(source_utils.get_info(title))
    except Exception:
        return set()


def _fallback_quality(title):
    try:
        from resources.lib.common import source_utils

        return source_utils.get_quality(title)
    except Exception:
        t = title.lower()
        if "2160" in t or "4k" in t:
            return "4K"
        if "1080" in t:
            return "1080p"
        if "720" in t:
            return "720p"
        return "SD"


def build_info(parsed, title):
    info = _fallback_info(title)
    if not parsed:
        return info
    for tag in parsed.get("visualTags") or []:
        info |= VISUAL_MAP.get(tag.upper(), set())
    for tag in parsed.get("audioTags") or []:
        mapped = AUDIO_MAP.get(tag.upper())
        if mapped:
            info.add(mapped)
    for ch in parsed.get("audioChannels") or []:
        if ch in ("2.0", "5.1", "7.1"):
            info.add(ch)
    enc = ENCODE_MAP.get((parsed.get("encode") or "").upper())
    if enc:
        info.add(enc)
    info |= QUALITY_MAP.get((parsed.get("quality") or "").upper(), set())
    # Seren-regels: DV + HDR samen = HYBRID, DD+ wint van DD
    if "DV" in info and "HDR" in info:
        info.add("HYBRID")
    if "DD+" in info:
        info.discard("DD")
    if "SDR" in info and ("HDR" in info or "DV" in info):
        info.discard("SDR")
    return info


def _with_headers(url, behavior_hints):
    headers = ((behavior_hints or {}).get("proxyHeaders") or {}).get("request") or {}
    if not headers:
        return url
    return "{}|{}".format(url, urlencode(headers))


def convert_streams(streams, include_uncached=False, number_titles=True):
    """Zet een AIOStreams-antwoord om naar Seren-bronnen (pure functie, testbaar)."""
    results = []
    for stream in streams or []:
        url = stream.get("url")
        data = stream.get("streamData") or {}
        stype = (data.get("type") or "").lower()
        if not url or stype in SKIP_TYPES:
            continue
        service = data.get("service") or {}
        if not include_uncached and service and service.get("cached") is False:
            continue
        hints = stream.get("behaviorHints") or {}
        parsed = data.get("parsedFile") or {}
        title = (
            data.get("filename")
            or hints.get("filename")
            or data.get("folderName")
            or (stream.get("description") or "").split("\n")[0]
            or stream.get("name")
            or "AIOStreams"
        )
        title = title.strip()
        size = data.get("size") or hints.get("videoSize")
        quality = RESOLUTION_MAP.get(parsed.get("resolution") or "") or _fallback_quality(title)

        label = "AIO"
        if service.get("id"):
            label = "AIO|{}".format(service["id"].upper())
        elif data.get("addon"):
            label = "AIO|{}".format(str(data["addon"]).upper())

        source = {
            "url": _with_headers(url, hints),
            "release_title": title,
            "quality": quality,
            "info": build_info(parsed, title),
            "provider_name_override": label,
        }
        if isinstance(size, (int, float)) and size > 0:
            source["size"] = int(size / 1024 / 1024)  # Seren rekent in MB
        results.append(source)

    if number_titles and results:
        width = max(2, len(str(len(results))))
        for i, source in enumerate(results, 1):
            source["release_title"] = "{}. {}".format(str(i).zfill(width), source["release_title"])
    return results


class AIOStreamsScraper(object):
    def __init__(self):
        self.base_url = base_url_from_manifest(_seren_setting("aiostreams.manifest_url"))
        self.include_uncached = _bool_setting("aiostreams.include_uncached", False)
        self.number_titles = _bool_setting("aiostreams.keep_order", True)
        try:
            self.timeout = max(5, int(_seren_setting("aiostreams.timeout") or 30))
        except (TypeError, ValueError):
            self.timeout = 30

    def _fetch(self, media_type, stremio_id):
        if not self.base_url:
            _log("No manifest URL set. Enter it in the package settings.", "warning")
            return []
        url = "{}/stream/{}/{}.json".format(self.base_url, media_type, quote(stremio_id, safe=":"))
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=self.timeout)
            resp.raise_for_status()
            streams = resp.json().get("streams", [])
        except Exception as e:  # network/JSON errors must not crash Seren
            # Never log str(e): requests puts the full URL (with the encrypted
            # AIOStreams config / debrid keys) in its error messages.
            status = getattr(getattr(e, "response", None), "status_code", None)
            _log(
                "Request failed for {}: {}{}".format(
                    stremio_id, type(e).__name__, " (HTTP {})".format(status) if status else ""
                ),
                "error",
            )
            return []
        results = convert_streams(streams, self.include_uncached, self.number_titles)
        _log("{} sources found for {}".format(len(results), stremio_id))
        return results

    def movie(self, imdb=None, tmdb=None):
        if imdb:
            return self._fetch("movie", imdb)
        if tmdb:
            return self._fetch("movie", "tmdb:{}".format(tmdb))
        return []

    def episode(self, imdb=None, tmdb=None, season=None, episode=None):
        if not season or not episode:
            return []
        if imdb:
            return self._fetch("series", "{}:{}:{}".format(imdb, season, episode))
        if tmdb:
            return self._fetch("series", "tmdb:{}:{}:{}".format(tmdb, season, episode))
        return []
