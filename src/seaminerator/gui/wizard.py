from __future__ import annotations

import time

from aqt import mw
from aqt.operations import CollectionOp, QueryOp
from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import showWarning

from ..addon_config import config_from_dict
from ..anki.batch import create_batch
from ..anki.collection_client import CollectionAnkiClient
from ..anki.notetype import NOTE_TYPE_NAME, ensure_notetype
from ..core.ai.gemini_rest import GeminiError, GeminiRestConnector
from ..core.cards import highlight_html
from ..core.flow import CardResult
from ..core.models import WordBlock
from ..core.prompt import load_prompt
from ..core.session import (
    count_selected,
    default_selection,
    selected_sentences,
    summarize,
)

PAGE_INPUT = 0
PAGE_REVIEW = 1
PAGE_SUMMARY = 2


class MineWizard(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Mine vocabulary")
        self.resize(720, 560)

        config = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
        self._cfg = config_from_dict(config)
        self._client = CollectionAnkiClient(mw.col)
        self._blocks: list[WordBlock] = []
        self._selection: dict[int, set[int]] = {}
        self._results: list[CardResult] = []
        self._creating = False
        self._started_at = 0.0

        self._pages = QStackedWidget(self)
        self._pages.addWidget(self._build_input_page())

        layout = QVBoxLayout(self)
        layout.addWidget(self._pages)

    def _build_input_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("Paste the list of the day, one item per line:"))
        self._words_edit = QTextEdit(page)
        layout.addWidget(self._words_edit)

        row = QHBoxLayout()
        row.addWidget(QLabel("Target deck:"))
        self._deck_box = QComboBox(page)
        decks = sorted(self._client.deck_names())
        self._deck_box.addItems(decks)
        if self._cfg.default_deck in decks:
            self._deck_box.setCurrentText(self._cfg.default_deck)
        row.addWidget(self._deck_box, stretch=1)
        layout.addLayout(row)

        self._mine_button = QPushButton("Mine", page)
        self._mine_button.clicked.connect(self._start_mining)
        layout.addWidget(self._mine_button)

        return page

    def _words(self) -> list[str]:
        raw = self._words_edit.toPlainText()
        return [line.strip() for line in raw.splitlines() if line.strip()]

    def _start_mining(self) -> None:
        if not self._cfg.gemini_api_key:
            showWarning(
                "No Gemini API key configured.\n\n"
                "Set it in Tools → Add-ons → Sea Minerator → Config.",
                parent=self,
            )
            return

        words = self._words()
        if not words:
            showWarning("Paste at least one word to mine.", parent=self)
            return
        if not self._deck_box.currentText():
            showWarning("Choose a target deck.", parent=self)
            return

        try:
            connector = GeminiRestConnector(self._cfg.gemini_api_key, self._cfg.model)
            prompt = load_prompt(self._cfg.prompt_path)
        except Exception as exc:
            showWarning(
                f"Could not start mining: {exc}\n\n"
                f"Check the prompt file configured at '{self._cfg.prompt_path}'.",
                parent=self,
                textFormat="plain",
            )
            return

        self._started_at = time.monotonic()
        self._mine_button.setEnabled(False)

        op = QueryOp(
            parent=self,
            op=lambda _col: connector.mine(words, prompt),
            success=self._on_mined,
        )
        op.failure(self._on_mining_failed)
        op.without_collection().with_progress(
            f"Mining {len(words)} item(s)…"
        ).run_in_background()

    def _on_mining_failed(self, exc: Exception) -> None:
        self._mine_button.setEnabled(True)
        if isinstance(exc, GeminiError):
            showWarning(str(exc), parent=self, textFormat="plain")
        else:
            showWarning(f"Mining failed: {exc}", parent=self, textFormat="plain")
        self._pages.setCurrentIndex(PAGE_INPUT)

    def _on_mined(self, blocks: list[WordBlock]) -> None:
        self._mine_button.setEnabled(True)
        if not blocks:
            showWarning("The model returned no words.", parent=self)
            return
        self._blocks = blocks
        try:
            ensure_notetype(mw.col, self._cfg.tts_lang)
        except Exception as exc:
            showWarning(
                f"Could not prepare the '{NOTE_TYPE_NAME}' note type: {exc}",
                parent=self,
                textFormat="plain",
            )
            return
        self._show_review()

    def _show_review(self) -> None:
        self._selection = default_selection(self._blocks)

        page = QWidget(self)
        outer = QVBoxLayout(page)

        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)

        for w_index, block in enumerate(self._blocks):
            inner_layout.addWidget(self._build_block_widget(w_index, block))

        inner_layout.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        footer = QHBoxLayout()
        self._count_label = QLabel("")
        footer.addWidget(self._count_label)
        footer.addStretch(1)
        self._create_button = QPushButton("Create cards", page)
        self._create_button.clicked.connect(self._create_cards)
        footer.addWidget(self._create_button)
        outer.addLayout(footer)

        self._pages.addWidget(page)
        self._pages.setCurrentIndex(PAGE_REVIEW)
        self._refresh_count()

    def _build_block_widget(self, w_index: int, block: WordBlock) -> QWidget:
        box = QFrame()
        box.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(box)

        header = f"<b>{block.expression}</b> — {block.grammar_class}"
        if block.translations:
            header += f" · {', '.join(block.translations)}"
        layout.addWidget(QLabel(header))

        if not block.sentences:
            empty = QLabel("no sentences returned for this word")
            empty.setEnabled(False)
            layout.addWidget(empty)
            return box

        for s_index, sentence in enumerate(block.sentences):
            checkbox = QCheckBox()
            checkbox.setChecked(s_index in self._selection.get(w_index, set()))
            checkbox.stateChanged.connect(
                lambda state, w=w_index, s=s_index: self._toggle(w, s, state)
            )

            label = QLabel(
                highlight_html(
                    sentence.text, sentence.highlight, self._cfg.highlight_color
                )
            )
            label.setWordWrap(True)

            row = QHBoxLayout()
            row.addWidget(checkbox)
            row.addWidget(label, stretch=1)
            layout.addLayout(row)

        return box

    def _toggle(self, w_index: int, s_index: int, state) -> None:
        chosen = self._selection.setdefault(w_index, set())
        if state:
            chosen.add(s_index)
        else:
            chosen.discard(s_index)
        self._refresh_count()

    def _refresh_count(self) -> None:
        total = count_selected(self._selection)
        self._count_label.setText(f"{total} sentence(s) selected")
        # `_creating` guards against a checkbox toggled while a batch is in
        # flight re-enabling Create: `_toggle` calls this method too, and
        # without the guard `total > 0` alone would flip the button back on
        # mid-operation, letting a second click launch a second CollectionOp
        # over the same (or a since-mutated) selection.
        self._create_button.setEnabled(total > 0 and not self._creating)

    def _create_cards(self) -> None:
        pairs = selected_sentences(self._blocks, self._selection)
        if not pairs:
            return

        deck = self._deck_box.currentText()

        def op(col):
            results, changes = create_batch(col, pairs, self._cfg, deck)
            self._results = results
            return changes

        self._creating = True
        self._refresh_count()
        CollectionOp(parent=self, op=op).success(self._on_cards_created).failure(
            self._on_create_failed
        ).run_in_background()

    def _on_cards_created(self, _changes) -> None:
        self._creating = False
        self._refresh_count()
        self._show_summary()

    def _on_create_failed(self, exc: Exception) -> None:
        self._creating = False
        self._refresh_count()
        showWarning(f"Could not create cards: {exc}", parent=self, textFormat="plain")

    def _show_summary(self) -> None:
        summary = summarize(self._results, time.monotonic() - self._started_at)

        page = QWidget(self)
        layout = QVBoxLayout(page)

        headline = f"<b>{summary.created} card(s) created</b> in {summary.elapsed}"
        if summary.failed:
            headline += f" · {summary.failed} failed"
        layout.addWidget(QLabel(headline))

        if summary.warnings:
            warnings = QTextEdit(page)
            warnings.setReadOnly(True)
            warnings.setPlainText("\n".join(summary.warnings))
            layout.addWidget(warnings)

        close = QPushButton("Close", page)
        close.clicked.connect(self.accept)
        layout.addWidget(close)

        self._pages.addWidget(page)
        self._pages.setCurrentIndex(PAGE_SUMMARY)
