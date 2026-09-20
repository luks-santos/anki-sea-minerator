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

    mw.seaminerator_wizard = MineWizard(mw)
    mw.seaminerator_wizard.show()
