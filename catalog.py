"""Compatibility entry point; implementation lives in esstu_schedule.catalog."""

import sys

from esstu_schedule import catalog as _implementation

sys.modules[__name__] = _implementation
