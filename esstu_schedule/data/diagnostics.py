"""Bounded, thread-safe diagnostics shared by parsing, HTTP and static builds."""

import logging
from collections import Counter, deque
from threading import RLock

LOGGER = logging.getLogger("esstu_schedule.data")
_lock, _counts, _recent = RLock(), Counter(), deque(maxlen=50)
_unparsed_cells = 0


def record_unparsed_cell():
    global _unparsed_cells
    with _lock:
        _unparsed_cells += 1


def record_error(source, message):
    LOGGER.warning("Incomplete schedule %s: %s", source, message)
    with _lock:
        _counts[str(source)] += 1
        _recent.append({"source": str(source), "message": str(message)})


def parsing_status():
    with _lock:
        return {
            "parse_error_count": sum(_counts.values()),
            "failed_source_count": len(_counts),
            "parse_errors": list(_recent),
            "unparsed_cell_count": _unparsed_cells,
        }


def reset_diagnostics():
    global _unparsed_cells
    with _lock:
        _counts.clear()
        _recent.clear()
        _unparsed_cells = 0
