from __future__ import annotations

from aqt import mw
from aqt.operations import CollectionOp
from aqt.qt import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    Qt,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import showInfo, showWarning

from ..addon_config import config_from_dict
from ..anki.batch import create_import_batch
from ..anki.collection_client import CollectionAnkiClient
from ..anki.notetype import NOTE_TYPE_NAME, ensure_notetype
from ..core.config import Config, ConfigError
from ..core.flow import CardResult
from ..core.models import ImportedCard, parse_imported_text
from ..core.session import summarize
from ..core.tags import BASE_TOPICS

ADDON = __name__.split(".")[0]


def open_importer(parent: QWidget | None = None) -> None:
    dialog = ImportDialog(parent or mw)
    dialog.exec()
    dialog.deleteLater()


class ImportDialog(QDialog):
    """Paste ready-made front/back pairs and create them as cards.

    No AI involved: each block of two lines (front, back) becomes one note,
    the back gets the chosen topic in parentheses, and a leading "[Label]"
    on the front becomes a CSS label that the audio does not read.
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import cards")
        self.resize(640, 520)

        try:
            config = config_from_dict(mw.addonManager.getConfig(ADDON) or {})
        except ConfigError:
            # Importing needs no AI provider; only deck, audio and colors.
            config = Config()
        self._cfg = config
        self._cards: list[ImportedCard] = []
        self._results: list[CardResult] = []
        self._creating = False
        self._closed = False

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Paste the cards: front line, back line, and a blank line "
                "between cards."
            )
        )
        self._text = QTextEdit(self)
        self._text.setAcceptRichText(False)
        self._text.textChanged.connect(self._refresh)
        layout.addWidget(self._text, stretch=1)

        form = QFormLayout()
        self._topic_box = QComboBox(self)
        self._topic_box.setEditable(True)
        self._topic_box.addItems([""] + list(BASE_TOPICS))
        self._topic_box.setCurrentText("")
        form.addRow("Topic:", self._topic_box)

        self._deck_box = QComboBox(self)
        decks = sorted(CollectionAnkiClient(mw.col).deck_names())
        self._deck_box.addItems(decks)
        if self._cfg.default_deck in decks:
            self._deck_box.setCurrentText(self._cfg.default_deck)
        form.addRow("Deck:", self._deck_box)
        layout.addLayout(form)

        footer = QHBoxLayout()
        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setTextFormat(Qt.TextFormat.PlainText)
        footer.addWidget(self._status, stretch=1)
        cancel = QPushButton("Cancel", self)
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        self._create_button = QPushButton("Create cards", self)
        self._create_button.clicked.connect(self._create)
        footer.addWidget(self._create_button)
        # Enter belongs to the text box and the topic field, never to a button.
        for button in (cancel, self._create_button):
            button.setAutoDefault(False)
        layout.addLayout(footer)

        self._refresh()

    def done(self, result: int) -> None:
        # A creation op still running checks this before touching widgets.
        self._closed = True
        super().done(result)

    def _refresh(self) -> None:
        self._cards, warnings = parse_imported_text(self._text.toPlainText())
        status = f"{len(self._cards)} card(s) ready"
        if warnings:
            status += f" · {len(warnings)} block(s) skipped:\n" + "\n".join(warnings)
        self._status.setText(status)
        self._create_button.setEnabled(bool(self._cards) and not self._creating)

    def _create(self) -> None:
        if not self._cards:
            return
        deck = self._deck_box.currentText()
        if not deck:
            showWarning("Choose a deck.", parent=self)
            return
        try:
            ensure_notetype(mw.col, self._cfg.tts_lang)
        except Exception as exc:
            showWarning(
                f"Could not prepare the '{NOTE_TYPE_NAME}' note type: {exc}",
                parent=self,
                textFormat="plain",
            )
            return

        cards = list(self._cards)
        topic = self._topic_box.currentText()

        def op(col):
            results, changes = create_import_batch(col, cards, self._cfg, deck, topic)
            self._results = results
            return changes

        self._creating = True
        self._refresh()
        CollectionOp(parent=self, op=op).success(self._on_created).failure(
            self._on_failed
        ).run_in_background()

    def _on_created(self, _changes) -> None:
        if self._closed:
            return
        self._creating = False
        summary = summarize(self._results, 0.0)
        message = f"{summary.created} card(s) created."
        if summary.failed:
            message += f" {summary.failed} failed:\n\n" + "\n".join(summary.warnings)
        showInfo(message, parent=self, textFormat="plain")
        self.accept()

    def _on_failed(self, exc: Exception) -> None:
        if self._closed:
            return
        self._creating = False
        self._refresh()
        showWarning(f"Could not create cards: {exc}", parent=self, textFormat="plain")
