from __future__ import annotations

import json

from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import showWarning

from ..addon_config import config_from_dict, config_to_dict
from ..anki.collection_client import CollectionAnkiClient
from ..core.ai.base import AIError
from ..core.ai.registry import build_provider
from ..core.config import PROVIDERS, Config, ConfigError, ProviderSettings
from ..core.settings import form_to_config, settings_from_form, validate, visible_fields

ADDON = __name__.split(".")[0]


def _load_config() -> Config:
    try:
        return config_from_dict(mw.addonManager.getConfig(ADDON) or {})
    except ConfigError:
        return Config()


def open_settings(parent: QWidget | None = None) -> bool:
    dialog = SettingsDialog(parent or mw)
    return bool(dialog.exec())


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sea Minerator settings")
        self.resize(560, 0)

        self._cfg = _load_config()
        # Edits to every provider's block live here until Save, so switching
        # the dropdown back and forth never loses a typed key.
        self._blocks: dict[str, ProviderSettings] = dict(self._cfg.providers)
        self._current = self._cfg.provider

        form = QFormLayout()

        self._provider_box = QComboBox()
        for provider_id, info in PROVIDERS.items():
            self._provider_box.addItem(info.display_name, provider_id)
        form.addRow("Provider:", self._provider_box)

        key_row = QHBoxLayout()
        self._key_edit = QLineEdit()
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        show_key = QPushButton("Show")
        show_key.setCheckable(True)
        show_key.toggled.connect(
            lambda on: self._key_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
            )
        )
        key_row.addWidget(self._key_edit, stretch=1)
        key_row.addWidget(show_key)
        self._key_label = QLabel("API key:")
        form.addRow(self._key_label, key_row)
        key_note = QLabel("Stored in plain text in Anki's add-on folder.")
        key_note.setEnabled(False)
        form.addRow("", key_note)

        self._url_edit = QLineEdit()
        self._url_label = QLabel("Base URL:")
        form.addRow(self._url_label, self._url_edit)

        model_row = QHBoxLayout()
        self._model_box = QComboBox()
        self._model_box.setEditable(True)
        load_models = QPushButton("Load models")
        load_models.clicked.connect(lambda: self._fetch_models(fill=True))
        model_row.addWidget(self._model_box, stretch=1)
        model_row.addWidget(load_models)
        form.addRow("Model:", model_row)

        test_row = QHBoxLayout()
        test_button = QPushButton("Test connection")
        test_button.clicked.connect(lambda: self._fetch_models(fill=False))
        self._status = QLabel("")
        test_row.addWidget(test_button)
        test_row.addWidget(self._status, stretch=1)
        form.addRow("", test_row)

        self._deck_box = QComboBox()
        decks = sorted(CollectionAnkiClient(mw.col).deck_names())
        self._deck_box.addItems([""] + decks)
        self._deck_box.setCurrentText(self._cfg.default_deck)
        form.addRow("Default deck:", self._deck_box)

        self._tts_edit = QLineEdit(self._cfg.tts_lang)
        form.addRow("Audio (TTS):", self._tts_edit)
        self._color_edit = QLineEdit(self._cfg.highlight_color)
        form.addRow("Highlight:", self._color_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        advanced = buttons.addButton("Advanced…", QDialogButtonBox.ButtonRole.ResetRole)
        advanced.clicked.connect(self._advanced)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._provider_box.setCurrentIndex(self._provider_box.findData(self._current))
        self._show_block(self._current)
        self._provider_box.currentIndexChanged.connect(self._on_provider_changed)

    def _show_block(self, provider_id: str) -> None:
        settings = self._blocks[provider_id]
        self._key_edit.setText(settings.api_key or "")
        self._url_edit.setText(settings.base_url)
        self._model_box.clear()
        self._model_box.setCurrentText(settings.model)
        visible = visible_fields(provider_id)
        self._url_label.setVisible("base_url" in visible)
        self._url_edit.setVisible("base_url" in visible)
        self._key_label.setText(
            "API key:" if PROVIDERS[provider_id].needs_key else "API key (optional):"
        )
        self._status.setText("")

    def _store_block(self) -> None:
        self._blocks[self._current] = settings_from_form(
            self._key_edit.text(),
            self._model_box.currentText(),
            self._url_edit.text(),
        )

    def _on_provider_changed(self, _index: int) -> None:
        self._store_block()
        self._current = self._provider_box.currentData()
        self._show_block(self._current)

    def _form_config(self) -> Config:
        self._store_block()
        return form_to_config(
            self._current,
            self._blocks,
            self._deck_box.currentText(),
            self._tts_edit.text(),
            self._color_edit.text(),
            self._cfg.prompt_path,
        )

    def _fetch_models(self, fill: bool) -> None:
        try:
            # Listing models is how a model gets chosen, so none is required.
            provider = build_provider(self._form_config(), require_model=False)
        except ConfigError as exc:
            self._status.setText(f"✗ {exc}")
            return

        self._status.setText("Connecting…")

        def on_success(models: list[str]) -> None:
            self._status.setText(f"✓ Connected — {len(models)} models available")
            if fill:
                current = self._model_box.currentText()
                self._model_box.clear()
                self._model_box.addItems(models)
                self._model_box.setCurrentText(current)

        def on_failure(exc: Exception) -> None:
            message = str(exc) if isinstance(exc, AIError) else f"failed: {exc}"
            self._status.setText(f"✗ {message}")

        QueryOp(
            parent=self, op=lambda _col: provider.list_models(), success=on_success
        ).failure(on_failure).without_collection().run_in_background()

    def _save(self) -> None:
        cfg = self._form_config()
        problems = validate(cfg)
        if problems:
            showWarning("\n".join(problems), parent=self, textFormat="plain")
            return
        mw.addonManager.writeConfig(ADDON, config_to_dict(cfg))
        self.accept()

    def _advanced(self) -> None:
        editor = _JsonEditor(self, config_to_dict(self._form_config()))
        if editor.exec():
            self._cfg = editor.result_config
            self._blocks = dict(self._cfg.providers)
            self._current = self._cfg.provider
            # Without blocking, setCurrentIndex fires _on_provider_changed,
            # which would store the form (still showing the old provider)
            # into the new provider's block and overwrite the JSON edit.
            self._provider_box.blockSignals(True)
            self._provider_box.setCurrentIndex(
                self._provider_box.findData(self._current)
            )
            self._provider_box.blockSignals(False)
            self._show_block(self._current)
            self._deck_box.setCurrentText(self._cfg.default_deck)
            self._tts_edit.setText(self._cfg.tts_lang)
            self._color_edit.setText(self._cfg.highlight_color)


class _JsonEditor(QDialog):
    """Raw JSON for advanced options such as `prompt_path`.

    Anki's own `aqt.addons.ConfigEditor` needs the Add-ons dialog as its
    parent, so this is a minimal stand-in that validates before accepting.
    """

    def __init__(self, parent: QWidget, data: dict) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sea Minerator — advanced config")
        self.resize(560, 480)
        self.result_config = Config()
        self._text = QPlainTextEdit(json.dumps(data, indent=2, ensure_ascii=False))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self._text)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        try:
            self.result_config = config_from_dict(json.loads(self._text.toPlainText()))
        except (ValueError, ConfigError) as exc:
            showWarning(f"Invalid config: {exc}", parent=self, textFormat="plain")
            return
        self.accept()
