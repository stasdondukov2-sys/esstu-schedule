"""Bounded, thread-safe diagnostics shared by parsing, HTTP and static builds."""

import logging
from collections import Counter, deque
from threading import RLock

LOGGER = logging.getLogger("esstu_schedule.data")
_lock, _counts, _recent = RLock(), Counter(), deque(maxlen=50)
_unparsed_cells = 0
_cells = Counter()


def record_cell(*, empty=False, lost=False, review=False):
    global _unparsed_cells
    with _lock:
        _cells["empty_cell_count"] += int(empty)
        _cells["lost_cell_count"] += int(lost)
        _cells["review_cell_count"] += int(review)
        _unparsed_cells += int(
            review
        )  # Legacy field: reviewable cells, not lost cells.


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
            **{
                key: _cells[key]
                for key in ("empty_cell_count", "lost_cell_count", "review_cell_count")
            },
        }


def reset_diagnostics():
    global _unparsed_cells
    with _lock:
        _counts.clear()
        _recent.clear()
        _unparsed_cells = 0
        _cells.clear()
