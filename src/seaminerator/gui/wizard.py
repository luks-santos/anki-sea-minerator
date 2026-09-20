from __future__ import annotations

import time

from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import showWarning

from ..addon_config import config_from_dict
from ..anki.collection_client import CollectionAnkiClient
from ..anki.notetype import NOTE_TYPE_NAME, ensure_notetype
from ..core.ai.gemini_rest import GeminiError, GeminiRestConnector
from ..core.models import WordBlock
from ..core.prompt import load_prompt

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
            )
            return
        self._show_review()

    def _show_review(self) -> None:
        raise NotImplementedError
