"""Compatibility entry point; implementation lives in esstu_schedule.cache_tools."""

import sys

from esstu_schedule import cache_tools as _implementation

sys.modules[__name__] = _implementation
