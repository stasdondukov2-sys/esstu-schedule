import json
from datetime import UTC, datetime, timedelta

import pytest

from scripts.smoke_site import check_site


def make_site(root, generated):
    api = root / "api"
    api.mkdir()
    (api / "status.json").write_text(
        json.dumps(
            {
                "generated_at": generated,
                "schema_version": 2,
                "build_id": "test-build",
            }
        )
    )
    for section in ("bakalavriat", "spezialitet", "zo1", "zo2"):
        (api / "groups").mkdir(exist_ok=True)
        (api / "groups" / f"{section}.json").write_text(
            json.dumps({"groups": [{"id": "99", "name": "Any new group"}]})
        )
        schedules = api / "schedule" / section
        schedules.mkdir(parents=True)
        (schedules / "99.json").write_text("{}")


def test_live_smoke_accepts_arbitrary_names_and_order(tmp_path):
    now = datetime(2026, 10, 17, tzinfo=UTC)
    make_site(tmp_path, now.isoformat())
    check_site(tmp_path, now=now, minimum_groups=4)


@pytest.mark.parametrize("delta", [-timedelta(hours=1), timedelta(hours=1)])
def test_smoke_rejects_stale_or_future_builds(tmp_path, delta):
    now = datetime(2026, 10, 17, tzinfo=UTC)
    make_site(tmp_path, (now + delta).isoformat())
    with pytest.raises(RuntimeError, match="generated_at"):
        check_site(tmp_path, now=now, minimum_groups=4)


def test_smoke_rejects_truncated_publication(tmp_path):
    now = datetime(2026, 10, 17, tzinfo=UTC)
    make_site(tmp_path, now.isoformat())
    with pytest.raises(RuntimeError, match="Too few groups"):
        check_site(tmp_path, now=now, minimum_groups=100)
    (tmp_path / "api/schedule/zo2/99.json").unlink()
    with pytest.raises(RuntimeError, match="Missing schedule"):
        check_site(tmp_path, now=now, minimum_groups=4)
