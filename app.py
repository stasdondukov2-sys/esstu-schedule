"""Compatibility entry point; implementation lives in esstu_schedule.app."""

import sys

from esstu_schedule import app as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
