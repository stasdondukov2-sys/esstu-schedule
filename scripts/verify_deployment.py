"""Assert that deployed HTML and API belong to the tested shell."""

import argparse
import json
import re
import time
import urllib.request


def verify(base, expected, attempts=5):
    for attempt in range(attempts):
        try:

            def fetch(path):
                request = urllib.request.Request(
                    base.rstrip("/")
                    + "/"
                    + path
                    + "?verification="
                    + str(time.time_ns()),
                    headers={"Cache-Control": "no-cache"},
                )
                with urllib.request.urlopen(request, timeout=10) as response:
                    return response.read().decode("utf-8")

            status = json.loads(fetch("api/status.json"))
            html = fetch("index.html")
            version = re.search(r'content="([^"]+)" name="app-version"', html)
            if (
                status.get("build_id") != expected
                or not version
                or version[1] != expected
            ):
                raise RuntimeError("Published build differs from tested build")
            print("Published HTML/API match tested build:", expected)
            return
        except (OSError, ValueError, RuntimeError):
            if attempt + 1 == attempts:
                raise
            time.sleep(2**attempt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected", required=True)
    args = parser.parse_args()
    verify(args.url, args.expected)
