"""Fingerprints describe the exact saved bytes, not the date of this build."""

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=8192)
def _digest(path, modified_ns, size):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def file_sha256(path):
    path = Path(path)
    stat = path.stat()
    return _digest(str(path.resolve()), stat.st_mtime_ns, stat.st_size)


def source_manifest(root, metadata):
    return {
        str(path.relative_to(root)).replace("\\", "/"): {
            **metadata.get(str(path.relative_to(root)).replace("\\", "/"), {}),
            "sha256": file_sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(root.glob("*/*.htm"))
    }


def build_provenance(sources, root):
    fingerprints = {name: entry["sha256"] for name, entry in sorted(sources.items())}
    digest = hashlib.sha256(
        json.dumps(fingerprints, sort_keys=True).encode()
    ).hexdigest()
    checked = []
    unknown = 0
    for entry in sources.values():
        try:
            value = datetime.fromisoformat(entry["retrieved_at"].replace("Z", "+00:00"))
            if value.tzinfo is None:
                raise ValueError("Source timestamp needs timezone")
            checked.append(value.astimezone(UTC))
        except (KeyError, ValueError, TypeError):
            unknown += 1
    commit = os.environ.get("GITHUB_SHA")
    if not commit:
        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=5
            ).strip()
        except (OSError, subprocess.SubprocessError):
            commit = None
    return {
        "code_revision": commit,
        "sources_sha256": digest,
        "source_count": len(sources),
        "source_checked_at_oldest": min(checked).isoformat() if checked else None,
        "source_checked_at_latest": max(checked).isoformat() if checked else None,
        "sources_without_check_date": unknown,
    }
