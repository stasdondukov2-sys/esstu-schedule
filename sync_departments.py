"""Compatibility entry point for scripts.sync_departments."""
import sys
if __name__ == "__main__":
    import runpy
    runpy.run_module("scripts.sync_departments", run_name="__main__")
else:
    from scripts import sync_departments as _implementation
    sys.modules[__name__] = _implementation
