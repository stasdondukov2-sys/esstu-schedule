"""Compatibility entry point; implementation lives in esstu_schedule.teachers."""
import sys
from esstu_schedule import teachers as _implementation
sys.modules[__name__] = _implementation
