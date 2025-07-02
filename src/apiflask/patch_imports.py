"""Patch module imports to support switching between implementations."""

import sys
from importlib import reload
from contextlib import contextmanager


@contextmanager
def patch_imports():
    """Context manager to reload modules after switching implementations."""
    # Store references to modules we need to reload
    modules_to_reload = []
    for name, module in list(sys.modules.items()):
        if name.startswith('apiflask'):
            modules_to_reload.append(name)
    
    try:
        yield
    finally:
        # Reload all apiflask modules to pick up the changes
        for name in modules_to_reload:
            if name in sys.modules:
                reload(sys.modules[name])
