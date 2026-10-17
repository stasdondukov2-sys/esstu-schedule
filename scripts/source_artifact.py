"""Restore a bounded retained source artifact; never use PR artifacts as trusted input."""

import hashlib
import json
import os
import subprocess
import tempfile
import shutil
from pathlib import Path


def run_gh(*args):
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, env=os.environ.copy()
    )
    if result.returncode:
        raise RuntimeError("Cannot read retained source artifact")
    return result.stdout


def restore_artifact(repository, destination, expected=None, name="source-snapshot"):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(
        run_gh("api", f"repos/{repository}/actions/artifacts?name={name}&per_page=20")
    )
    for artifact in data["artifacts"][:20]:
        if (
            artifact["expired"]
            or artifact.get("workflow_run", {}).get("head_branch") != "main"
        ):
            continue
        with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
            root = Path(temporary)
            run_gh(
                "run",
                "download",
                str(artifact["workflow_run"]["id"]),
                "--repo",
                repository,
                "--name",
                name,
                "--dir",
                str(root),
            )
            manifests = list(root.rglob("sources.json"))
            source = next(
                (
                    path.parent
                    for path in manifests
                    if (path.parent / "bakalavriat").exists()
                ),
                None,
            )
            if not source:
                continue
            if expected and any(
                not (source / path).is_file()
                or hashlib.sha256((source / path).read_bytes()).hexdigest()
                != entry["sha256"]
                for path, entry in expected.items()
            ):
                continue
            shutil.copytree(source, destination, dirs_exist_ok=True)
            if expected:
                from esstu_schedule.data.store import write_json_atomic

                write_json_atomic(destination / "sources.json", expected)
            print(
                "Restored source artifact",
                artifact["id"],
                "with verified source hashes" if expected else "",
            )
            return True
    return False


def restore_progress(repository, destination):
    """Resume only newer, hash-verified files; never replace the published API."""
    from datetime import datetime
    from esstu_schedule.data.store import write_json_atomic

    destination = Path(destination)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        root = Path(temporary) / "progress"
        if not restore_artifact(repository, root):
            return
        previous = json.loads(
            (destination / "sources.json").read_text(encoding="utf-8")
        )
        incoming = json.loads((root / "sources.json").read_text(encoding="utf-8"))
        copied = 0
        for name, entry in incoming.items():
            # Source manifests can only refer to a single section and an HTML file.
            relative = Path(name)
            if (
                relative.is_absolute()
                or len(relative.parts) != 2
                or ".." in relative.parts
                or relative.suffix != ".htm"
            ):
                continue
            source = root / relative
            if not source.is_file() or hashlib.sha256(
                source.read_bytes()
            ).hexdigest() != entry.get("sha256"):
                continue
            try:
                checked = datetime.fromisoformat(entry["retrieved_at"])
                old = datetime.fromisoformat(
                    previous.get(name, {}).get("retrieved_at")
                    or "1970-01-01T00:00:00+00:00"
                )
                if checked <= old:
                    continue
            except (ValueError, TypeError, KeyError):
                continue
            (destination / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination / relative)
            previous[name] = entry
            copied += 1
        # Negative observations never overwrite a last good positive source.
        for rejected in (root / ".negative").glob("*/*.json"):
            entry = json.loads(rejected.read_text(encoding="utf-8"))
            raw = rejected.with_suffix(".htm")
            relative = (
                rejected.relative_to(root / ".negative").with_suffix(".htm").as_posix()
            )
            current = (
                destination / ".negative" / rejected.relative_to(root / ".negative")
            )
            saved = (
                json.loads(current.read_text(encoding="utf-8"))
                if current.exists()
                else {}
            )
            try:
                stamp = datetime.fromisoformat(entry["checked_at"])
                latest = max(
                    datetime.fromisoformat(value or "1970-01-01T00:00:00+00:00")
                    for value in (
                        saved.get("checked_at"),
                        previous.get(relative, {}).get("retrieved_at"),
                    )
                )
                if (
                    stamp <= latest
                    or not raw.is_file()
                    or hashlib.sha256(raw.read_bytes()).hexdigest()
                    != entry.get("sha256")
                ):
                    continue
            except (ValueError, TypeError, KeyError):
                continue
            current.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(raw, current.with_suffix(".htm"))
            shutil.copy2(rejected, current)
        write_json_atomic(destination / "sources.json", previous)
        print("Resumed newer verified source files:", copied)


if __name__ == "__main__":
    restore_progress(os.environ["GITHUB_REPOSITORY"], Path("demo_data"))
