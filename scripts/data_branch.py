"""Durable validated data snapshots, stored separately from application history."""

import argparse
import base64
import os
import shutil
import subprocess
from pathlib import Path


def git(root, *arguments, check=True):
    environment = os.environ.copy()
    if environment.get("GITHUB_TOKEN"):
        environment.update(
            GIT_CONFIG_COUNT="1",
            GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
            GIT_CONFIG_VALUE_0="AUTHORIZATION: basic "
            + base64.b64encode(
                ("x-access-token:" + environment["GITHUB_TOKEN"]).encode()
            ).decode(),
        )
    result = subprocess.run(
        ["git", *arguments], cwd=root, env=environment, capture_output=True, text=True
    )
    if check and result.returncode:
        raise RuntimeError("Data branch git operation failed: " + arguments[0])
    return result


def restore(directory, repository, sources):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    git(directory, "init", "-q")
    git(directory, "config", "core.autocrlf", "false")
    git(directory, "remote", "add", "origin", repository)
    available = git(
        directory, "ls-remote", "--heads", "origin", "refs/heads/data"
    ).stdout.strip()
    if not available:
        from scripts.published_data import bootstrap

        owner, repo = repository.removesuffix(".git").rstrip("/").split("/")[-2:]
        bootstrap(directory, f"https://{owner}.github.io/{repo}/")
        return False
    git(directory, "fetch", "--depth=1", "origin", "data")
    git(directory, "checkout", "-B", "data", "FETCH_HEAD")
    if not (directory / "api/status.json").exists():
        raise RuntimeError("Data branch is missing a validated API")
    shutil.copytree(directory / "sources", sources, dirs_exist_ok=True)
    print("Restored durable validated sources and API")
    return True


def save(directory, site, sources, revision):
    directory = Path(directory)
    for name, source in [("api", Path(site) / "api"), ("sources", Path(sources))]:
        target = directory / name
        if target.resolve() == source.resolve():
            continue
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
    (directory / "README.md").write_text(
        "Validated API and source snapshots. Application revision: " + revision + "\n",
        encoding="utf-8",
    )
    git(directory, "config", "user.name", "github-actions[bot]")
    git(
        directory,
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    )
    git(directory, "add", "api", "sources", "README.md")
    if git(directory, "diff", "--cached", "--quiet", check=False).returncode == 0:
        print("Data unchanged")
        return
    git(directory, "checkout", "-B", "data")
    git(
        directory, "commit", "-m", "Update validated schedule data for " + revision[:12]
    )
    git(directory, "push", "origin", "HEAD:refs/heads/data")
    print("Validated data saved in branch data")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["restore", "save", "checkpoint"])
    parser.add_argument("--directory", type=Path, default=Path("preview/data"))
    parser.add_argument("--site", type=Path, default=Path("dist"))
    parser.add_argument("--sources", type=Path, default=Path("demo_data"))
    parser.add_argument(
        "--repository",
        default="https://github.com/"
        + os.environ.get("GITHUB_REPOSITORY", "stasdondukov2-sys/esstu-schedule")
        + ".git",
    )
    args = parser.parse_args()
    if args.mode == "restore":
        restore(args.directory, args.repository, args.sources)
    elif args.mode == "checkpoint":
        save(
            args.directory,
            args.directory,
            args.sources,
            os.environ.get("GITHUB_SHA", "local"),
        )
    else:
        save(
            args.directory,
            args.site,
            args.sources,
            os.environ.get("GITHUB_SHA", "local"),
        )
