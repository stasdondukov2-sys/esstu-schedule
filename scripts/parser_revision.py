"""Fingerprint the transformation applied to saved sources, not the UI release."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARSER_FILES = [
    "esstu_schedule/parser.py",
    "esstu_schedule/identity.py",
    "esstu_schedule/catalog.py",
    "esstu_schedule/teachers.py",
    "esstu_schedule/rooms.py",
    "esstu_schedule/data/models.py",
    "esstu_schedule/data/repository.py",
    "scripts/group_build.py",
    "scripts/group_freshness.py",
    "scripts/parser_revision.py",
    "scripts/build_static_site.py",
    "scripts/publication.py",
    "esstu_schedule/data/provenance.py",
    "requirements.txt",
]


def parser_revision():
    digest = hashlib.sha256()
    for name in PARSER_FILES:
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update((ROOT / name).read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()[:16]
