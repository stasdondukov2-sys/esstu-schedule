"""Select per-group fallbacks and keep code-only releases independent of data quality."""

import argparse
import json
import shutil
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

from esstu_schedule.data.store import write_json_atomic
from esstu_schedule.parser import normalize_group_name


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def source_is_recent(schedule, now, max_age_days=7):
    try:
        checked = datetime.fromisoformat(
            (schedule.get("source_checked_at") or "").replace("Z", "+00:00")
        )
        return timedelta(0) <= now - checked <= timedelta(days=max_age_days)
    except (KeyError, TypeError, ValueError):
        return False


def last_good_group(candidate, previous, now=None, max_age_days=7):
    if not candidate.get("is_incomplete") or not previous:
        return candidate
    if not any(character.isalnum() for character in candidate.get("group_name", "")):
        return candidate
    if previous.get("is_incomplete") or normalize_group_name(
        previous.get("group_name", "")
    ) != normalize_group_name(candidate.get("group_name", "")):
        return candidate
    try:
        checked = datetime.fromisoformat(
            (previous.get("source_checked_at") or "").replace("Z", "+00:00")
        )
        age = (now or datetime.now(UTC)) - checked
        if not timedelta(0) <= age <= timedelta(days=max_age_days):
            return candidate
    except (KeyError, TypeError, ValueError):
        return candidate
    result = deepcopy(previous)
    result.update(
        group_id=candidate["group_id"],
        resolved_group_id=candidate["group_id"],
        is_stale_fallback=True,
        source_mode="last_good_json",
        fallback_reason=candidate.get("parse_errors", []),
        origin_source_file=previous.get("source_file"),
    )
    return result


def previous_groups(root):
    if not root:
        return {}
    groups = {}
    for path in (Path(root) / "api/schedule").glob("*/*.json"):
        item = read_json(path)
        if not item.get("is_incomplete"):
            groups[
                (item.get("section"), normalize_group_name(item.get("group_name", "")))
            ] = item
    return groups


def reuse_api(site, baseline, expected_build):
    site, baseline = Path(site), Path(baseline)
    current = read_json(site / "api/status.json")
    if current["build_id"] != expected_build:
        raise RuntimeError("Publication shell differs from tested shell")
    previous = read_json(baseline / "api/status.json")
    # Stage the complete previous API before replacing anything in the new site.
    staged = site / "previous-api"
    shutil.copytree(baseline / "api", staged)
    shutil.rmtree(site / "api")
    staged.rename(site / "api")
    previous.update(
        build_id=expected_build,
        code_revision=current["code_revision"],
        code_deployed_at=current["generated_at"],
    )
    write_json_atomic(site / "api/status.json", previous)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, default=Path("dist"))
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--mode", choices=["code", "data"], required=True)
    parser.add_argument("--expected-build", required=True)
    args = parser.parse_args()
    status = read_json(args.site / "api/status.json")
    if status["build_id"] != args.expected_build:
        raise RuntimeError("Publication shell differs from tested shell")
    if (
        args.mode == "code"
        and args.baseline
        and (args.baseline / "api/status.json").exists()
    ):
        reuse_api(args.site, args.baseline, args.expected_build)
        print(
            "Code release: previous API reused byte-for-byte except shell provenance in status"
        )
    elif (
        args.mode == "code"
        and __import__("os").environ.get("GITHUB_REF") == "refs/heads/main"
    ):
        raise RuntimeError(
            "Code publication requires previous published API or durable data branch"
        )
    elif args.mode == "code":
        print(
            "Review build: committed test sources retained; data quality gate applies only to data releases"
        )
    else:
        from scripts.check_sync import check_parse_quality

        check_parse_quality(args.site, baseline=args.baseline)
