"""A partial failed download is visible to Actions and cannot be published as success."""

import json
from pathlib import Path


def check_reports(root):
    for name in ("department-sync.json", "group-sync.json"):
        report = json.loads((root / name).read_text(encoding="utf-8"))
        if not report.get("downloaded") or report.get("failed"):
            raise RuntimeError(
                f"{name}: downloaded={len(report.get('downloaded', []))}; failed={len(report.get('failed', []))}"
            )


if __name__ == "__main__":
    check_reports(Path(__file__).resolve().parents[1] / "demo_data")
