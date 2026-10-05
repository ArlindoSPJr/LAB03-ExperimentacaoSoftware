"""Cache em disco: um arquivo JSON por chave (nome = sha1 da chave)."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib


class DiskCache:
    def __init__(self, root: pathlib.Path):
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> pathlib.Path:
        return self.root / (hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json")

    def get(self, key: str) -> dict | list | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None  # arquivo truncado (ex.: Ctrl+C): trata como miss

    def set(self, key: str, value) -> None:
        path = self._path(key)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)  # escrita atômica
