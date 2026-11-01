# -*- coding: utf-8 -*-

import re
from urllib.parse import unquote_plus
from providerModules.a4kScrapers import core

# TorrentDownload (ported from POV 6.10.20). Result rows link to /<40-char hash>/<release-name>, so
# the hash and the full release name come straight from the search page (the visible link text is
# truncated); size and seeders are in the row's own cells. Up to two result pages are read; the second
# only when the first came back (nearly) full - a full page holds 50 rows.
_FULL_PAGE_MIN_ROWS = 40
# The site black-holes roughly a third of searches (connection and TLS succeed, no answer ever comes),
# while a good answer takes well under a second. A short timeout plus one retry turns a lost query
# into a few seconds' delay instead of a lost query or a 10 s stall.
_REQUEST_TIMEOUT = 4
_ATTEMPTS = 2
_ROW_RE = re.compile(
    r'href="/([0-9A-Fa-f]{40})/([^"]+)".*?'
    r'<td class="tdnormal">[^<]*</td>\s*<td class="tdnormal">([^<]*)</td>\s*<td class="tdseed">([^<]*)</td>',
    re.DOTALL)


class sources(core.DefaultSources):
    def __init__(self, *args, **kwargs):
        # The site answers parallel requests with sporadic 404s (page 1 as well as page 2), so every
        # query of one scrape goes through a single sequential request queue.
        kwargs.setdefault('request', core.Request(sequental=True, wait=0.5, timeout=_REQUEST_TIMEOUT))
        super(sources, self).__init__(__name__, *args, **kwargs)

    @staticmethod
    def _forgive_failure(page_url):
        # a4k's per-domain circuit breaker counts every failed attempt; a retried page must count once,
        # not twice. Returns False when the breaker has already tripped (no point retrying then).
        try:
            from providerModules.a4kScrapers import request as _rq
            domain = _rq._get_domain(page_url)
            with _rq._cb_lock:
                if domain in _rq._cb_dead_until:
                    return False
                if _rq._cb_failures.get(domain, 0) > 0:
                    _rq._cb_failures[domain] -= 1
        except Exception:
            pass
        return True

    def _get_page(self, page_url):
        response = None
        for attempt in range(_ATTEMPTS):
            response = self._request.get(page_url)
            if response is not None and response.status_code == 200:
                return response
            if self._request.exc_msg == 'circuit breaker open':
                break
            if attempt < _ATTEMPTS - 1 and not self._forgive_failure(page_url):
                break
        return response

    def _search_request(self, url, query):
        if not query:
            return []
        request_url = (url.base + url.search) % core.quote_plus(query)
        any_success = False
        results = []
        for page in ['', '&p=2']:
            response = self._get_page(request_url + page)
            if response is None or response.status_code != 200:
                continue
            any_success = True
            rows = _ROW_RE.findall(response.text)
            for hash_, slug, size_text, seeds_text in rows:
                try:
                    seeds = int(seeds_text.replace(',', '').strip() or 0)
                except Exception:
                    seeds = 0
                results.append({
                    'title': unquote_plus(slug).replace('&amp;', '&'),
                    'hash': hash_.upper(),
                    'size_text': size_text.strip(),
                    'seeds': seeds,
                })
            if not page and len(rows) < _FULL_PAGE_MIN_ROWS:
                break
        if not any_success:
            self._request.exc_msg = ''
            return None
        return results

    def _soup_filter(self, response):
        return response

    def _title_filter(self, el):
        return el.get('title', '')

    def _info(self, el, url, torrent):
        torrent['hash'] = el.get('hash', '')
        try:
            torrent['size'] = core.source_utils.de_string_size(el.get('size_text', ''))
        except Exception:
            torrent['size'] = 0
        torrent['seeds'] = el.get('seeds', 0)
        return torrent
