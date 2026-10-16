"""Compatibility entry point; implementation lives in esstu_schedule.rooms."""

import sys

from esstu_schedule import rooms as _implementation

sys.modules[__name__] = _implementation
