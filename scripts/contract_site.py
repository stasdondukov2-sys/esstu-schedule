"""Run the new shell against the exact previous API, including its old schema."""

import shutil
import json
from pathlib import Path


def prepare(
    site=Path("dist"),
    baseline=Path("preview/data"),
    target=Path("preview/contract-site"),
):
    count = 0
    for section in ("bakalavriat", "spezialitet", "zo1", "zo2"):
        groups = json.loads(
            (baseline / f"api/groups/{section}.json").read_text(encoding="utf-8")
        )["groups"]
        if not groups:
            raise RuntimeError("Empty published group catalog: " + section)
        for group in groups:
            schedule = json.loads(
                (baseline / f"api/schedule/{section}/{group['id']}.json").read_text(
                    encoding="utf-8"
                )
            )
            if not isinstance(schedule.get("weeks"), dict):
                raise RuntimeError("Incompatible published group schedule")
        count += len(groups)
    if count < 100:
        raise RuntimeError("Published catalog is unexpectedly small")
    for section in ("bakalavriat", "spezialitet"):
        teachers = json.loads(
            (baseline / f"api/teachers/all/{section}.json").read_text(encoding="utf-8")
        )["teachers"]
        if not teachers:
            raise RuntimeError("Empty published teacher catalog")
    rooms = json.loads((baseline / "api/rooms.json").read_text(encoding="utf-8"))[
        "rooms"
    ]
    if not isinstance(rooms, list) or not rooms:
        raise RuntimeError("Empty/incompatible published rooms")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(site, target, ignore=shutil.ignore_patterns("api"))
    shutil.copytree(baseline / "api", target / "api")
    print(
        "Published API contract smoke OK:",
        count,
        "groups; original API bytes preserved",
    )


if __name__ == "__main__":
    prepare()
