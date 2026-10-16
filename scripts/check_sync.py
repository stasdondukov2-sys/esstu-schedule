"""A partial failed download is visible to Actions and cannot be published as success."""

import argparse
import json
import os
from pathlib import Path


def check_reports(root, allow_partial=False):
    validated = 0
    for name in ("department-sync.json", "group-sync.json"):
        report = json.loads((root / name).read_text(encoding="utf-8"))
        validated += len(report.get("downloaded", []))
        if not allow_partial and (not report.get("downloaded") or report.get("failed")):
            raise RuntimeError(
                f"{name}: downloaded={len(report.get('downloaded', []))}; failed={len(report.get('failed', []))}"
            )

    if not validated:
        raise RuntimeError("No source validated; keep the previous data publication")


def check_parse_quality(site, max_error_rate=None, baseline=None, max_regression=None):
    if max_error_rate is None:
        max_error_rate = float(os.environ.get("ESSTU_MAX_PARSE_ERROR_RATE", "0.25"))
    if max_regression is None:
        max_regression = float(os.environ.get("ESSTU_MAX_PARSE_REGRESSION", "0.01"))
    if not 0 <= max_regression <= 1:
        raise ValueError("max_regression must be between 0 and 1")
    if not 0 <= max_error_rate <= 1:
        raise ValueError("max_error_rate must be between 0 and 1")
    status = json.loads((Path(site) / "api/status.json").read_text(encoding="utf-8"))
    total, failed = (
        status.get("group_expected_count", 0),
        status.get("group_failed_count", 0),
    )
    if (
        not isinstance(total, int)
        or total <= 0
        or not isinstance(failed, int)
        or not 0 <= failed <= total
    ):
        raise RuntimeError("Parser coverage is missing or invalid")
    ratio = failed / total
    allowed = max_error_rate
    if baseline and (Path(baseline) / "api/status.json").exists():
        previous = json.loads(
            (Path(baseline) / "api/status.json").read_text(encoding="utf-8")
        )
        previous_total = previous.get("group_expected_count", 0)
        previous_failed = previous.get("group_failed_count", 0)
        catalogs = list((Path(baseline) / "api/groups").glob("*.json"))
        if catalogs:
            from esstu_schedule.data.repository import group_identity_error

            previous_total = previous_failed = 0
            for catalog in catalogs:
                for group in json.loads(catalog.read_text(encoding="utf-8"))["groups"]:
                    previous_total += 1
                    path = (
                        Path(baseline)
                        / "api/schedule"
                        / catalog.stem
                        / (str(group["id"]) + ".json")
                    )
                    old = (
                        json.loads(path.read_text(encoding="utf-8"))
                        if path.exists()
                        else {"is_incomplete": True}
                    )
                    previous_failed += bool(
                        old.get("is_incomplete")
                        or group_identity_error(old, group["name"])
                    )
        if previous_total:
            allowed = min(allowed, previous_failed / previous_total + max_regression)
    if ratio > allowed:
        raise RuntimeError(
            f"Publication blocked: {failed}/{total} group schedules failed ({ratio:.1%}), allowed {allowed:.1%}"
        )
    print(f"Parser quality OK: {failed}/{total} group schedules failed ({ratio:.1%})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument(
        "--max-error-rate",
        type=float,
        default=float(os.environ.get("ESSTU_MAX_PARSE_ERROR_RATE", "0.25")),
    )
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    if args.site:
        check_parse_quality(args.site, args.max_error_rate, args.baseline)
    else:
        check_reports(
            Path(__file__).resolve().parents[1] / "demo_data", args.allow_partial
        )
