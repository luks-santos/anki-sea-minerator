from __future__ import annotations

import json

from aqt import mw
from aqt.operations import QueryOp
from aqt.qt import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    Qt,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import showWarning

from ..addon_config import config_from_dict, config_to_dict, display_config
from ..anki.collection_client import CollectionAnkiClient
from ..core.ai.base import AIError
from ..core.ai.registry import build_provider
from ..core.config import (
    PROVIDERS,
    TTS_SPEED_MAX,
    TTS_SPEED_MIN,
    Config,
    ConfigError,
    ProviderSettings,
    voice_names,
)
from ..core.settings import (
    form_to_config,
    mask_keys,
    model_choices,
    settings_from_form,
    unmask_keys,
    validate,
    visible_fields,
    voice_choices,
)
from .voices import installed_voices, preview

ADDON = __name__.split(".")[0]


def _load_config() -> Config:
    # A broken provider part must not reset deck, audio and color on Save.
    return display_config(mw.addonManager.getConfig(ADDON) or {})


def open_settings(parent: QWidget | None = None) -> bool:
    # From the Add-ons dialog there is no explicit parent; the active window
    # (that dialog) keeps the settings on top of it instead of behind.
    dialog = SettingsDialog(parent or QApplication.activeWindow() or mw)
    saved = bool(dialog.exec())
    dialog.deleteLater()
    return saved


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sea Minerator settings")
        self.resize(560, 0)

        self._cfg = _load_config()
        self._closed = False
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
        self._load_button = QPushButton("Load models")
        self._load_button.clicked.connect(lambda: self._fetch_models(fill=True))
        model_row.addWidget(self._model_box, stretch=1)
        model_row.addWidget(self._load_button)
        form.addRow("Model:", model_row)

        test_row = QHBoxLayout()
        self._test_button = QPushButton("Test connection")
        self._test_button.clicked.connect(lambda: self._fetch_models(fill=False))
        # Error bodies can be long or HTML; wrap them and never render markup.
        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setTextFormat(Qt.TextFormat.PlainText)
        test_row.addWidget(self._test_button)
        test_row.addWidget(self._status, stretch=1)
        form.addRow("", test_row)

        self._deck_box = QComboBox()
        decks = sorted(CollectionAnkiClient(mw.col).deck_names())
        self._deck_box.addItems([""] + decks)
        self._deck_box.setCurrentText(self._cfg.default_deck)
        form.addRow("Default deck:", self._deck_box)

        self._tts_edit = QLineEdit(self._cfg.tts_lang)
        self._tts_edit.editingFinished.connect(self._fill_voices)
        form.addRow("Audio (TTS):", self._tts_edit)

        self._installed = installed_voices()
        voice_row = QHBoxLayout()
        # Editable so voices this computer lacks (a phone's) can be typed
        # after a comma; picking from the list replaces the text.
        self._voice_box = QComboBox()
        self._voice_box.setEditable(True)
        self._voice_box.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._voice_box.lineEdit().setPlaceholderText("Any voice for the language")
        preview_button = QPushButton("▶ Preview")
        preview_button.clicked.connect(self._preview)
        voice_row.addWidget(self._voice_box, stretch=1)
        voice_row.addWidget(preview_button)
        form.addRow("Voice:", voice_row)

        self._speed_box = QDoubleSpinBox()
        self._speed_box.setRange(TTS_SPEED_MIN, TTS_SPEED_MAX)
        self._speed_box.setSingleStep(0.1)
        self._speed_box.setDecimals(2)
        form.addRow("Speed:", self._speed_box)

        self._voice_note = QLabel("")
        self._voice_note.setWordWrap(True)
        self._voice_note.setEnabled(False)
        form.addRow("", self._voice_note)
        self._show_voice(self._cfg)

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

    def done(self, result: int) -> None:
        # A Load models / Test connection op may still be running when the
        # dialog closes; its callbacks check this and touch no widget.
        self._closed = True
        super().done(result)

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
            tts_voices=self._voice_box.currentText(),
            tts_speed=self._speed_box.value(),
        )

    def _show_voice(self, cfg: Config) -> None:
        self._fill_voices()
        self._voice_box.setCurrentText(", ".join(cfg.tts_voices))
        self._speed_box.setValue(cfg.tts_speed)

    def _fill_voices(self) -> None:
        lang = self._tts_edit.text().strip()
        choices = voice_choices(self._installed, lang)
        typed = self._voice_box.currentText()
        self._voice_box.clear()
        self._voice_box.addItems(choices)
        # Adding items to an empty editable box selects the first one.
        self._voice_box.setCurrentText(typed)
        if choices:
            where = "Lists only this computer's voices; add a phone's after a comma."
        else:
            where = f"No {lang or 'language'} voices found on this computer."
        self._voice_note.setText(
            f"{where} Blank uses the first voice for the language. "
            "Applies the next time you create or import cards."
        )

    def _preview(self) -> None:
        preview(
            self._tts_edit.text().strip(),
            voice_names(self._voice_box.currentText().split(",")),
            self._speed_box.value(),
        )

    def _fetch_models(self, fill: bool) -> None:
        try:
            # Listing models is how a model gets chosen, so none is required.
            provider = build_provider(self._form_config(), require_model=False)
        except ConfigError as exc:
            self._status.setText(f"✗ {exc}")
            return

        self._status.setText("Connecting…")
        self._set_fetching(True)
        provider_id = self._current

        def finished() -> bool:
            # False when the result no longer applies: the dialog closed, or
            # the user switched provider while the request was running.
            if self._closed:
                return False
            self._set_fetching(False)
            return self._current == provider_id

        def on_success(models: list[str]) -> None:
            if not finished():
                return
            choices = model_choices(models)
            self._status.setText(f"✓ Connected — {len(choices)} models available")
            if fill:
                current = self._model_box.currentText()
                self._model_box.clear()
                self._model_box.addItems(choices)
                self._model_box.setCurrentText(current)

        def on_failure(exc: Exception) -> None:
            if not finished():
                return
            message = str(exc) if isinstance(exc, AIError) else f"failed: {exc}"
            self._status.setText(f"✗ {message}")

        QueryOp(
            parent=self, op=lambda _col: provider.list_models(), success=on_success
        ).failure(on_failure).without_collection().run_in_background()

    def _set_fetching(self, fetching: bool) -> None:
        # One request at a time: repeated clicks would start concurrent ops.
        self._load_button.setEnabled(not fetching)
        self._test_button.setEnabled(not fetching)

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
            self._show_voice(self._cfg)
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
        # Stored keys are shown masked; a mask left as-is keeps the key.
        self._original = data
        self._text = QPlainTextEdit(
            json.dumps(mask_keys(data), indent=2, ensure_ascii=False)
        )
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
            edited = json.loads(self._text.toPlainText())
            if not isinstance(edited, dict):
                raise ValueError("the config must be a JSON object")
            self.result_config = config_from_dict(unmask_keys(edited, self._original))
        except (ValueError, ConfigError) as exc:
            showWarning(f"Invalid config: {exc}", parent=self, textFormat="plain")
            return
        self.accept()
