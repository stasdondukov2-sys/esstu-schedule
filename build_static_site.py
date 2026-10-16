"""Compatibility entry point for scripts.build_static_site."""

import sys

if __name__ == "__main__":
    import runpy

    runpy.run_module("scripts.build_static_site", run_name="__main__")
else:
    from scripts import build_static_site as _implementation

    sys.modules[__name__] = _implementation
