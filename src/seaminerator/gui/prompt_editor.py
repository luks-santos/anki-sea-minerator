from __future__ import annotations

from aqt.qt import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import showWarning

from ..core.languages import NATIVE_LANGUAGES
from ..core.prompt import default_prompt
from ..core.settings import prompt_status, store_prompt


class PromptEditor(QDialog):
    """Edits one language's mining prompt.

    Nothing is written to the config here: on OK, `prompts` holds the
    updated edits, and the settings dialog keeps them until its own Save.
    """

    def __init__(self, parent: QWidget, code: str, prompts: dict[str, str]) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Mining prompt — {NATIVE_LANGUAGES[code].label}")
        self.resize(640, 520)
        self.prompts = dict(prompts)
        self._code = code
        self._default = default_prompt(code)

        self._status = QLabel("")
        self._text = QPlainTextEdit(prompts.get(code, self._default))
        self._text.textChanged.connect(self._show_status)
        note = QLabel(
            "The response format and the tagging rules are always added "
            "after this text."
        )
        note.setWordWrap(True)
        note.setEnabled(False)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        reset = buttons.addButton(
            "Reset to default", QDialogButtonBox.ButtonRole.ResetRole
        )
        reset.clicked.connect(lambda: self._text.setPlainText(self._default))

        layout = QVBoxLayout(self)
        layout.addWidget(self._status)
        layout.addWidget(self._text)
        layout.addWidget(note)
        layout.addWidget(buttons)
        self._show_status()

    def _show_status(self) -> None:
        self._status.setText(prompt_status(self._text.toPlainText(), self._default))

    def _accept(self) -> None:
        try:
            self.prompts = store_prompt(
                self.prompts, self._code, self._text.toPlainText(), self._default
            )
        except ValueError as exc:
            showWarning(str(exc), parent=self, textFormat="plain")
            return
        self.accept()
