"""Compatibility entry point; implementation lives in esstu_schedule.parser."""
import sys
from esstu_schedule import parser as _implementation
sys.modules[__name__] = _implementation
