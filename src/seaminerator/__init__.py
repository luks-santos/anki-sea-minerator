from __future__ import annotations

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "_vendor"))

try:
    from aqt import mw
except ImportError:  # running under pytest, outside Anki
    mw = None

if mw is not None:
    from .gui.menu import setup_menu

    setup_menu()
