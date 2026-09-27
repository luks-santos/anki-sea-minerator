from __future__ import annotations

from aqt import mw
from aqt.qt import QAction


def setup_menu() -> None:
    action = QAction("Mine vocabulary…", mw)
    action.triggered.connect(_open_wizard)
    mw.form.menuTools.addAction(action)
    mw.seaminerator_action = action

    settings_action = QAction("Sea Minerator settings…", mw)
    settings_action.triggered.connect(_open_settings)
    mw.form.menuTools.addAction(settings_action)
    mw.seaminerator_settings_action = settings_action

    # Tools → Add-ons → Config opens the settings dialog instead of Anki's
    # raw JSON editor.
    mw.addonManager.setConfigAction(__name__.split(".")[0], _open_settings)


def _open_settings() -> None:
    from .settings import open_settings

    open_settings()


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
