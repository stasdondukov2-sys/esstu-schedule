"""Bounded, thread-safe diagnostics shared by parsing, HTTP and static builds."""
import logging
from collections import Counter, deque
from threading import RLock

LOGGER = logging.getLogger('esstu_schedule.data')
_lock, _counts, _recent = RLock(), Counter(), deque(maxlen=50)


def record_error(source, message):
    LOGGER.warning('Incomplete schedule %s: %s', source, message)
    with _lock:
        _counts[str(source)] += 1
        _recent.append({'source': str(source), 'message': str(message)})


def parsing_status():
    with _lock:
        return {'parse_error_count': sum(_counts.values()), 'failed_source_count': len(_counts),
                'parse_errors': list(_recent)}


def reset_diagnostics():
    with _lock:
        _counts.clear()
        _recent.clear()
