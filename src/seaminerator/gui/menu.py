from __future__ import annotations

from aqt import mw
from aqt.qt import QAction


def setup_menu() -> None:
    action = QAction("Mine vocabulary…", mw)
    action.triggered.connect(_open_wizard)
    mw.form.menuTools.addAction(action)
    mw.seaminerator_action = action


def _open_wizard() -> None:
    from .wizard import MineWizard

    # A second click while the wizard is open brings it forward instead of
    # replacing it: replacing would drop the only reference to a dialog that
    # may still have a mining op running.
    current = getattr(mw, "seaminerator_wizard", None)
    if current is not None and current.isVisible():
        current.raise_()
        current.activateWindow()
        return

    mw.seaminerator_wizard = MineWizard(mw)
    mw.seaminerator_wizard.show()
