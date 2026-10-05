"""Cliente da API REST do GitHub: cache em disco, rate limit, backoff e paginação.

Usa `requests` diretamente (bibliotecas de acesso à API do GitHub são proibidas).
"""
from __future__ import annotations

import time
from urllib.parse import urlencode

import requests
from requests.structures import CaseInsensitiveDict

from pipeline.cache import DiskCache

API_URL = "https://api.github.com"
TIMEOUT = 30
SECONDARY_WAIT = 60  # s; recomendação do GitHub para limite secundário sem Retry-After


class GitHubError(Exception):
    def __init__(self, status: int | None, url: str, message: str = ""):
        super().__init__(f"HTTP {status} em {url}: {message}")
        self.status = status
        self.url = url


class NotFoundError(GitHubError):
    """404: recurso inexistente (ex.: tag apagada no compare)."""


def _json(resp):
    try:
        return resp.json()
    except ValueError:
        return None


def _message(resp) -> str:
    data = _json(resp)
    return data.get("message", "") if isinstance(data, dict) else ""


class GitHubClient:
    def __init__(self, token: str, cache: DiskCache, sleep=time.sleep, max_retries: int = 5):
        self.cache = cache
        self.sleep = sleep
        self.max_retries = max_retries
        self.clock = time.time
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    @staticmethod
    def _url(path: str) -> str:
        return path if path.startswith("http") else f"{API_URL}/{path.lstrip('/')}"

    @staticmethod
    def _key(url: str, params: dict | None) -> str:
        return f"{url}?{urlencode(sorted(params.items()))}" if params else url

    def get(self, path: str, params: dict | None = None) -> tuple[object, dict]:
        """Retorna (json, headers); usa o cache em disco. 404 levanta NotFoundError."""
        url = self._url(path)
        key = self._key(url, params)
        cached = self.cache.get(key)
        if cached is not None:
            return cached["json"], CaseInsensitiveDict(cached["headers"])
        data, headers = self._request(url, params)
        self.cache.set(key, {"json": data, "headers": dict(headers)})
        return data, headers

    def _request(self, url: str, params: dict | None):
        """Faz a requisição com tentativas; só retorna respostas 2xx (as únicas cacheadas)."""
        for attempt in range(self.max_retries + 1):
            last = attempt == self.max_retries
            try:
                resp = self.session.get(url, params=params, timeout=TIMEOUT)
            except (requests.ConnectionError, requests.Timeout) as exc:
                if last:
                    raise GitHubError(None, url, f"erro de rede: {exc}") from exc
                self.sleep(2 ** attempt)
                continue
            status = resp.status_code
            headers = CaseInsensitiveDict(resp.headers)
            if status == 404:
                raise NotFoundError(status, url, _message(resp))
            if status >= 500:
                if last:
                    raise GitHubError(status, url, _message(resp))
                self.sleep(2 ** attempt)
                continue
            if status in (403, 429):
                wait = self._rate_limit_wait(status, headers, resp)
                if wait is None:
                    raise GitHubError(status, url, _message(resp))
                if last:
                    raise GitHubError(status, url, "limite de requisições persistente")
                self.sleep(wait)
                continue
            if status >= 400:
                raise GitHubError(status, url, _message(resp))
            reset = self._reset_wait(headers)
            if reset is not None and reset > 0:
                self.sleep(reset)  # cota acabou: espera renovar antes da próxima chamada
            return _json(resp), headers

    def _reset_wait(self, headers) -> float | None:
        """Segundos até X-RateLimit-Reset quando a cota primária acabou; None caso contrário."""
        if headers.get("X-RateLimit-Remaining") != "0" or "X-RateLimit-Reset" not in headers:
            return None
        return float(headers["X-RateLimit-Reset"]) - self.clock()

    def _rate_limit_wait(self, status: int, headers, resp) -> float | None:
        """Espera para um 403/429 de rate limit; None se for 403 de permissão."""
        if "Retry-After" in headers:
            try:
                return int(headers["Retry-After"])
            except ValueError:
                return SECONDARY_WAIT
        reset = self._reset_wait(headers)
        if reset is not None:
            return max(reset, 1)
        if status == 429 or "rate limit" in _message(resp).lower():
            return SECONDARY_WAIT
        return None

    def rate_limit(self) -> dict:
        """GET /rate_limit (não consome cota); nunca usa o cache."""
        data, _ = self._request(self._url("/rate_limit"), None)
        return data
