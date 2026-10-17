"""A shared soft deadline stops scheduling work and lets publication continue."""

import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

_deadline = None


def set_deadline(seconds):
    global _deadline
    _deadline = time.monotonic() + seconds


def remaining():
    return (
        max(0, _deadline - time.monotonic()) if _deadline is not None else float("inf")
    )


def require_time():
    if remaining() <= 0:
        raise TimeoutError("Synchronization soft deadline reached")


def download_targets(targets, fetch):
    targets = iter(sorted(set(targets)))
    pending = {}
    with ThreadPoolExecutor(max_workers=4) as pool:

        def fill():
            while len(pending) < 4 and remaining() > 0:
                path = next(targets, None)
                if path is None:
                    break
                pending[pool.submit(fetch, path)] = path

        fill()
        while pending:
            completed, _ = wait(
                pending, timeout=min(1, remaining()), return_when=FIRST_COMPLETED
            )
            for future in completed:
                path = pending.pop(future)
                try:
                    yield path, future.result(), None
                except Exception as error:
                    yield path, None, error
            if remaining() <= 0:
                for future, path in list(pending.items()):
                    if future.cancel():
                        pending.pop(future)
                # At most four in-flight reads complete with their bounded timeout.
                for future, path in list(pending.items()):
                    try:
                        yield path, future.result(), None
                    except Exception as error:
                        yield path, None, error
                break
            fill()
