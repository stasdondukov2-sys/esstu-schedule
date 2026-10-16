"""Validate a publication without tying live portal data to browser fixtures."""

import json
from datetime import UTC, datetime
from pathlib import Path


def check_site(root: Path, now: datetime | None = None, minimum_groups: int = 100):
    now = now or datetime.now(UTC)
    status = json.loads((root / "api/status.json").read_text(encoding="utf-8"))
    generated = datetime.fromisoformat(
        status.get("code_deployed_at", status["generated_at"]).replace("Z", "+00:00")
    )
    if generated.tzinfo is None or not -300 <= (now - generated).total_seconds() <= 900:
        raise RuntimeError(
            "Publication status is missing a recent timezone-aware generated_at"
        )
    total = 0
    for section in ("bakalavriat", "spezialitet", "zo1", "zo2"):
        groups = json.loads(
            (root / f"api/groups/{section}.json").read_text(encoding="utf-8")
        )["groups"]
        if not groups:
            raise RuntimeError(f"Empty group catalog: {section}")
        total += len(groups)
        for group in groups:
            path = root / f"api/schedule/{section}/{group['id']}.json"
            if not path.is_file():
                raise RuntimeError(f"Missing schedule: {section}/{group['id']}")
    if total < minimum_groups:
        raise RuntimeError(f"Too few groups: {total} < {minimum_groups}")
    if status.get("schema_version", 1) not in (1, 2) or not status.get("build_id"):
        raise RuntimeError("Missing publication schema/build identity")
    print(
        f"Publication smoke OK: {total} groups, recent status, compatible schema, build {status['build_id']}"
    )


if __name__ == "__main__":
    check_site(Path(__file__).resolve().parents[1] / "dist")
