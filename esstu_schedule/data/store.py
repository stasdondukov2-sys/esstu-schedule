"""Read immutable, atomically published room snapshots; no request-time rebuild."""

import json
import os
import tempfile
from functools import lru_cache
from pathlib import Path


def write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False)
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


@lru_cache(maxsize=4)
def _read_snapshot(path, mtime_ns, size):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload.get("rooms"), list) or payload.get("count") != len(
        payload["rooms"]
    ):
        raise ValueError("Invalid prebuilt rooms index")
    return payload


def read_rooms_index(default_path):
    path = Path(os.environ.get("ESSTU_ROOMS_INDEX", default_path))
    try:
        stat = path.stat()
        return _read_snapshot(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    except (OSError, ValueError) as error:
        raise RuntimeError(
            "Индекс аудиторий недоступен. Требуется фоновая сборка."
        ) from error
