from __future__ import annotations

from aqt import mw
from aqt.operations import CollectionOp
from aqt.qt import (
    QColor,
    QComboBox,
    QDialog,
    QFont,
    QFormLayout,
    QHBoxLayout,
    QKeySequence,
    QLabel,
    QMessageBox,
    QPushButton,
    QShortcut,
    Qt,
    QTextCharFormat,
    QTextCursor,
    QTextEdit,
    QTextFormat,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import showWarning

from ..addon_config import display_config
from ..anki.batch import create_import_batch
from ..anki.collection_client import CollectionAnkiClient
from ..anki.notetype import NOTE_TYPE_NAME, ensure_notetype
from ..core.audio.recording import RecordingRun, run_notes
from ..core.flow import CardResult, ImportPlan, imported_speech, prepare_import
from ..core.session import (
    failure_lines,
    import_status,
    selection_on_lines,
    summarize,
    toggle_highlights,
    warning_lines,
)
from ..core.tags import BASE_TOPICS
from .recording import record_then

ADDON = __name__.split(".")[0]
# Marks highlighted text in the paste box, whatever color it is drawn in.
_HIGHLIGHT = QTextFormat.Property.UserProperty + 1


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

        # Importing needs no AI provider, only deck and audio settings, which
        # display_config keeps even when the provider part is broken.
        self._cfg = display_config(mw.addonManager.getConfig(ADDON) or {})
        self._plan = ImportPlan(cards=[], warnings=[], topic="")
        self._results: list[CardResult] = []
        self._run: RecordingRun | None = None
        self._creating = False
        self._closed = False

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Paste the cards: front line, back line, and a blank line "
                "between cards. Select part of a card and press Ctrl+B to "
                "highlight it."
            )
        )
        self._text = QTextEdit(self)
        # Pasted text stays plain: only Ctrl+B adds a highlight.
        self._text.setAcceptRichText(False)
        self._text.textChanged.connect(self._refresh)
        self._text.cursorPositionChanged.connect(self._type_plain)
        layout.addWidget(self._text, stretch=1)

        self._highlight_format = QTextCharFormat()
        self._highlight_format.setProperty(_HIGHLIGHT, True)
        self._highlight_format.setForeground(QColor(self._cfg.highlight_color))
        self._highlight_format.setFontWeight(QFont.Weight.DemiBold)
        highlight_row = QHBoxLayout()
        highlight_row.addStretch(1)
        self._highlight_button = QPushButton("Highlight (Ctrl+B)", self)
        self._highlight_button.clicked.connect(self._toggle_highlight)
        highlight_row.addWidget(self._highlight_button)
        layout.addLayout(highlight_row)
        QShortcut(QKeySequence("Ctrl+B"), self._text).activated.connect(
            self._toggle_highlight
        )

        form = QFormLayout()
        self._topic_box = QComboBox(self)
        self._topic_box.setEditable(True)
        self._topic_box.addItems([""] + list(BASE_TOPICS))
        self._topic_box.setCurrentText("")
        # The topic is validated too (e.g. "???" normalizes to nothing).
        self._topic_box.currentTextChanged.connect(self._refresh)
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
        self._cancel_button = QPushButton("Cancel", self)
        self._cancel_button.clicked.connect(self.reject)
        footer.addWidget(self._cancel_button)
        self._create_button = QPushButton("Create cards", self)
        self._create_button.clicked.connect(self._create)
        footer.addWidget(self._create_button)
        # Enter belongs to the text box and the topic field, never to a button.
        for button in (
            self._highlight_button,
            self._cancel_button,
            self._create_button,
        ):
            button.setAutoDefault(False)
        layout.addLayout(footer)

        self._refresh()

    def reject(self) -> None:
        # Cancel, Esc and the title-bar X all land here. While the cards are
        # being created, closing would hide the summary of what was created.
        if self._creating:
            return
        super().reject()

    def done(self, result: int) -> None:
        # A creation op still running checks this before touching widgets.
        self._closed = True
        super().done(result)

    def _refresh(self) -> None:
        self._plan = prepare_import(
            self._text.toPlainText(),
            self._topic_box.currentText(),
            self._highlight_ranges(),
        )
        highlighted = sum(
            1 for card in self._plan.cards if card.highlights or card.back_highlights
        )
        self._status.setText(
            import_status(
                len(self._plan.cards), self._plan.warnings, highlighted=highlighted
            )
        )
        self._create_button.setEnabled(bool(self._plan.cards) and not self._creating)
        self._cancel_button.setEnabled(not self._creating)

    def _highlight_ranges(self) -> list[tuple[int, int]]:
        # Document positions match toPlainText offsets: each block break is
        # one character there and one "\n" here.
        ranges: list[tuple[int, int]] = []
        block = self._text.document().begin()
        while block.isValid():
            fragments = block.begin()
            while not fragments.atEnd():
                fragment = fragments.fragment()
                if fragment.charFormat().boolProperty(_HIGHLIGHT):
                    start = fragment.position()
                    ranges.append((start, start + fragment.length()))
                fragments += 1
            block = block.next()
        return ranges

    def _toggle_highlight(self) -> None:
        cursor = self._text.textCursor()
        if not cursor.hasSelection():
            return
        # Line breaks and the blank lines between cards are left out.
        selected = selection_on_lines(
            self._text.toPlainText(), cursor.selectionStart(), cursor.selectionEnd()
        )
        if selected:
            self._paint(toggle_highlights(self._highlight_ranges(), selected))

    def _paint(self, ranges: list[tuple[int, int]]) -> None:
        # One edit block, so Ctrl+Z undoes a highlight in one step.
        cursor = QTextCursor(self._text.document())
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QTextCharFormat())
        for start, end in ranges:
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            cursor.mergeCharFormat(self._highlight_format)
        cursor.endEditBlock()

    def _type_plain(self) -> None:
        # Text typed next to a highlight would take its format: only Ctrl+B
        # highlights. With a selection, setCurrentCharFormat would restyle it.
        if not self._text.textCursor().hasSelection():
            self._text.setCurrentCharFormat(QTextCharFormat())

    def _create(self) -> None:
        if not self._plan.cards:
            return
        deck = self._deck_box.currentText()
        if not deck:
            showWarning("Choose a deck.", parent=self)
            return
        try:
            ensure_notetype(
                mw.col,
                self._cfg.tts_lang,
                self._cfg.tts_voices,
                self._cfg.tts_speed,
                audio=self._cfg.audio.source != "system",
            )
        except Exception as exc:
            showWarning(
                f"Could not prepare the '{NOTE_TYPE_NAME}' note type: {exc}",
                parent=self,
                textFormat="plain",
            )
            return

        cards = list(self._plan.cards)
        topic = self._plan.topic
        texts = imported_speech(cards, self._cfg, CollectionAnkiClient(mw.col))

        self._creating = True
        self._refresh()
        record_then(
            self,
            self._cfg,
            texts,
            lambda run: self._create_batch(cards, deck, topic, run),
        )

    def _create_batch(
        self, cards, deck: str, topic: str, run: RecordingRun | None
    ) -> None:
        if self._closed:
            return
        self._run = run

        def op(col):
            results, changes = create_import_batch(
                col, cards, self._cfg, deck, topic, run
            )
            self._results = results
            return changes

        CollectionOp(parent=self, op=op).success(self._on_created).failure(
            self._on_failed
        ).run_in_background()

    def _on_created(self, _changes) -> None:
        if self._closed:
            return
        self._creating = False
        summary = summarize(self._results, 0.0)
        box = QMessageBox(self)
        box.setWindowTitle("Import cards")
        box.setTextFormat(Qt.TextFormat.PlainText)
        text = f"{summary.created} card(s) created."
        if summary.failed:
            text += f" {summary.failed} failed (see details)."
        notes = run_notes(self._run)
        if notes:
            text += "\n\n" + "\n".join(notes)
        # Details are a scrollable area, so hundreds of lines never push the
        # OK button off-screen; each line names its card.
        details = failure_lines(self._results) + warning_lines(self._results)
        if details:
            box.setDetailedText("\n".join(details))
        box.setText(text)
        box.exec()
        self.accept()

    def _on_failed(self, exc: Exception) -> None:
        if self._closed:
            return
        self._creating = False
        self._refresh()
        showWarning(f"Could not create cards: {exc}", parent=self, textFormat="plain")
