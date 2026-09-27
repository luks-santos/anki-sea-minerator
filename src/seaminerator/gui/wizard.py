from __future__ import annotations

import html
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
from ..core.ai.base import AIError
from ..core.ai.registry import build_provider
from ..core.cards import highlight_html
from ..core.config import Config, ConfigError
from ..core.flow import CardResult
from ..core.mining import mine_words
from ..core.models import WordBlock
from ..core.prompt import load_prompt
from ..core.session import (
    apply_class_overrides,
    count_selected,
    default_selection,
    parse_word_list,
    selected_sentences,
    sentence_details,
    start_error,
    summarize,
    toggle_selection,
)
from ..core.tags import CLASS_TAGS, topic_vocabulary


class _NoWheelComboBox(QComboBox):
    # The review screen is a scroll area with one class combo per word. A
    # stock QComboBox eats wheel events even without focus (the default on
    # Windows and Linux styles), so scrolling past a combo would silently
    # change that word's class. Ignoring the event hands it to the scroll area.
    def wheelEvent(self, event) -> None:
        event.ignore()


class MineWizard(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Mine vocabulary")
        self.resize(720, 560)

        config = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
        self._config_error: str | None = None
        try:
            self._cfg = config_from_dict(config)
        except ConfigError as exc:
            # The review screen still needs colors and a deck list, so fall
            # back to defaults; mining is refused until the config is fixed.
            self._cfg = Config()
            self._config_error = str(exc)
        self._client = CollectionAnkiClient(mw.col)
        self._blocks: list[WordBlock] = []
        self._selection: dict[int, set[int]] = {}
        self._checkboxes: dict[int, list[QCheckBox]] = {}
        self._class_overrides: dict[int, str] = {}
        self._results: list[CardResult] = []
        self._creating = False
        self._closed = False
        self._started_at = 0.0

        self._pages = QStackedWidget(self)
        self._input_page = self._build_input_page()
        self._pages.addWidget(self._input_page)

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

    def done(self, result: int) -> None:
        # Every way out of the dialog (Close, Cancel, Esc, the title-bar X)
        # ends here. A mining or card-creation op still running in the
        # background checks this flag in its callback and drops the result
        # instead of rebuilding pages on a dialog that is already gone.
        self._closed = True
        super().done(result)

    def _config_problem(self, message: str) -> None:
        # The settings dialog shows what is missing; `message` is kept for
        # the callers, which pass the ConfigError text.
        from .settings import open_settings

        if open_settings(self):
            config = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
            try:
                self._cfg = config_from_dict(config)
                self._config_error = None
            except ConfigError as exc:
                self._config_error = str(exc)

    def _start_mining(self) -> None:
        words = parse_word_list(self._words_edit.toPlainText())
        error = start_error(words, self._deck_box.currentText())
        if error:
            showWarning(error, parent=self)
            return
        if self._config_error:
            self._config_problem(self._config_error)
            return
        try:
            provider = build_provider(self._cfg)
        except ConfigError as exc:
            self._config_problem(str(exc))
            return

        try:
            prompt = load_prompt(self._cfg.prompt_path)
        except Exception as exc:
            showWarning(
                f"Could not start mining: {exc}\n\n"
                f"Check the prompt file configured at '{self._cfg.prompt_path}'.",
                parent=self,
                textFormat="plain",
            )
            return

        # The collection's tags only refine the topic names Gemini is offered;
        # if they can't be read, mining still works with the base topics.
        try:
            collection_tags = self._client.tag_names()
        except Exception:
            collection_tags = []
        topics = topic_vocabulary(collection_tags)

        self._started_at = time.monotonic()
        self._mine_button.setEnabled(False)

        op = QueryOp(
            parent=self,
            op=lambda _col: mine_words(provider, words, prompt, topics),
            success=self._on_mined,
        )
        op.failure(self._on_mining_failed)
        op.without_collection().with_progress(
            f"Mining {len(words)} item(s)…"
        ).run_in_background()

    def _on_mining_failed(self, exc: Exception) -> None:
        if self._closed:
            return
        self._mine_button.setEnabled(True)
        if isinstance(exc, AIError):
            showWarning(str(exc), parent=self, textFormat="plain")
        else:
            showWarning(f"Mining failed: {exc}", parent=self, textFormat="plain")
        self._pages.setCurrentWidget(self._input_page)

    def _on_mined(self, blocks: list[WordBlock]) -> None:
        if self._closed:
            return
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
        self._checkboxes = {}
        self._class_overrides = {}

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
        cancel_button = QPushButton("Cancel", page)
        cancel_button.clicked.connect(self.reject)
        footer.addWidget(cancel_button)
        self._create_button = QPushButton("Create cards", page)
        self._create_button.clicked.connect(self._create_cards)
        footer.addWidget(self._create_button)
        outer.addLayout(footer)
        # QDialog push buttons are auto-default, so Enter clicks one of them.
        # On this page that could create the cards from inside the class
        # combo's text field, so no button here reacts to Enter.
        for button in page.findChildren(QPushButton):
            button.setAutoDefault(False)

        self._pages.addWidget(page)
        self._pages.setCurrentWidget(page)
        self._refresh_count()

    def _build_block_widget(self, w_index: int, block: WordBlock) -> QWidget:
        box = QFrame()
        box.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(box)

        # Model-supplied text lands in a rich-text QLabel unescaped, a `<`
        # would garble the label and QLabel will happily fetch an `<img
        # src=...>` it finds in there -- escape everything except the
        # sentence labels below, which are intentionally HTML produced by
        # `highlight_html`.
        header_row = QHBoxLayout()
        header_row.addWidget(QLabel(f"<b>{html.escape(block.expression)}</b> —"))

        class_box = _NoWheelComboBox()
        class_box.setEditable(True)
        class_box.addItems(CLASS_TAGS)
        if block.class_tag not in CLASS_TAGS:
            class_box.addItem(block.class_tag)
        # `setCurrentText` on an editable combo only sets the edit text and
        # leaves the index on the first item; select the item itself.
        class_box.setCurrentIndex(class_box.findText(block.class_tag))
        # Raw text is stored as-is; `apply_class_overrides` normalizes it and
        # falls back to the model's class when it is blank.
        class_box.currentTextChanged.connect(
            lambda text, w=w_index: self._class_overrides.__setitem__(w, text)
        )
        header_row.addWidget(class_box)

        translations_text = ""
        if block.translations:
            translations_text = "· " + ", ".join(
                html.escape(t) for t in block.translations
            )
        header_row.addWidget(QLabel(translations_text), stretch=1)

        if block.sentences:
            all_button = QPushButton("All")
            none_button = QPushButton("None")
            all_button.clicked.connect(lambda: self._set_all(w_index, True))
            none_button.clicked.connect(lambda: self._set_all(w_index, False))
            header_row.addWidget(all_button)
            header_row.addWidget(none_button)

        layout.addLayout(header_row)

        if block.explanation:
            explanation = QLabel(
                f'<span style="color:gray">{html.escape(block.explanation)}</span>'
            )
            explanation.setWordWrap(True)
            layout.addWidget(explanation)

        if not block.sentences:
            empty = QLabel("no sentences returned for this word")
            empty.setEnabled(False)
            layout.addWidget(empty)
            return box

        checkboxes: list[QCheckBox] = []
        for s_index, sentence in enumerate(block.sentences):
            checkbox = QCheckBox()
            # `setChecked` must run before `.connect`: with the connection
            # already wired up, this initial set would fire `_toggle` ->
            # `_refresh_count` -> `self._count_label`, which does not exist
            # yet at this point (it is only created once every block widget
            # has been built), raising an AttributeError.
            checkbox.setChecked(s_index in self._selection.get(w_index, set()))
            checkbox.toggled.connect(
                lambda checked, w=w_index, s=s_index: self._toggle(w, s, checked)
            )
            checkboxes.append(checkbox)

            label_html = highlight_html(
                sentence.text, sentence.highlight, self._cfg.highlight_color
            )
            details = sentence_details(sentence)
            if details:
                label_html += (
                    f' <span style="color:gray">· {html.escape(details)}</span>'
                )
            label = QLabel(label_html)
            label.setWordWrap(True)

            row = QHBoxLayout()
            row.addWidget(checkbox)
            row.addWidget(label, stretch=1)
            layout.addLayout(row)

        self._checkboxes[w_index] = checkboxes
        return box

    def _toggle(self, w_index: int, s_index: int, checked: bool) -> None:
        toggle_selection(self._selection, w_index, s_index, checked)
        self._refresh_count()

    def _set_all(self, w_index: int, checked: bool) -> None:
        sentence_count = len(self._blocks[w_index].sentences)
        self._selection[w_index] = set(range(sentence_count)) if checked else set()
        # The selection above is already authoritative for this word, so the
        # per-checkbox `setChecked` calls below must not re-enter `_toggle`
        # (each would fire `toggled` and fight over the same set). Block
        # each checkbox's signals for the duration of the visual update
        # instead of letting the handlers run.
        for checkbox in self._checkboxes.get(w_index, []):
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            checkbox.blockSignals(False)
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
        blocks = apply_class_overrides(self._blocks, self._class_overrides)
        pairs = selected_sentences(blocks, self._selection)
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
        if self._closed:
            return
        self._creating = False
        self._refresh_count()
        self._show_summary()

    def _on_create_failed(self, exc: Exception) -> None:
        if self._closed:
            return
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
        self._pages.setCurrentWidget(page)
