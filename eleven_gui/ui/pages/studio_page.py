from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from eleven_gui.accessibility import AccessibleTabWidget, configure_focusable_text_edit, defer_tab_order_chain
from eleven_gui.ui.widgets import AudioResultCard, CollapsibleSection, SectionCard, VoiceSettingsEditor, build_icon


OUTPUT_FORMATS = [
    "mp3_44100_192",
    "mp3_44100_128",
    "mp3_44100_96",
    "mp3_44100_64",
    "mp3_44100_32",
    "mp3_22050_32",
    "opus_48000_192",
    "opus_48000_128",
    "opus_48000_96",
    "opus_48000_64",
    "opus_48000_32",
    "wav_48000",
    "wav_44100",
    "wav_32000",
    "wav_24000",
    "wav_22050",
    "wav_16000",
    "wav_8000",
    "pcm_44100",
    "pcm_24000",
    "pcm_22050",
    "pcm_16000",
    "ulaw_8000",
    "alaw_8000",
]

COMMON_LANGUAGE_CODES = [
    "tr",
    "en",
    "ar",
    "de",
    "es",
    "fr",
    "it",
    "ja",
    "ko",
    "pt",
    "ru",
    "zh",
]


class StudioPage(QWidget):
    tts_requested = Signal(object)
    sts_requested = Signal(object)
    replay_result_requested = Signal()
    stop_result_requested = Signal()
    regenerate_result_requested = Signal()
    download_result_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.sts_audio_path: Path | None = None
        self._voices_by_id: dict[str, dict] = {}
        self._models_by_id: dict[str, dict] = {}
        self.setAccessibleName("Studio page")
        self.setAccessibleDescription("Generate speech with a selected voice or convert one recording into another voice.")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title = QLabel("Studio")
        title.setProperty("role", "title")
        subtitle = QLabel(
            "A calmer workspace for writing, converting and previewing audio without exposing every control at once."
        )
        subtitle.setProperty("role", "muted")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.context_status = QLabel("No voice has been routed here yet. You can still choose one manually.")
        self.context_status.setProperty("role", "muted")
        self.context_status.setAccessibleName("Studio status")
        self.context_status.setWordWrap(True)
        layout.addWidget(self.context_status)

        self.tabs = AccessibleTabWidget("Studio sections", "Switch between text to speech and speech to speech.")
        self.tabs.addTab(self._build_tts_tab(), "Text to &Speech")
        self.tabs.addTab(self._build_sts_tab(), "Speech to Speec&h")
        layout.addWidget(self.tabs, 1)

        self.result_card = AudioResultCard("Generated Audio")
        self.result_card.replay_requested.connect(self.replay_result_requested.emit)
        self.result_card.stop_requested.connect(self.stop_result_requested.emit)
        self.result_card.regenerate_requested.connect(self.regenerate_result_requested.emit)
        self.result_card.download_requested.connect(self.download_result_requested.emit)
        layout.addWidget(self.result_card)

        self.initial_focus_widget = self.tabs.tabBar()
        self._update_tts_button_state()
        self._update_sts_button_state()

    def _build_tts_tab(self) -> QWidget:
        tab = QWidget()
        tab.setAccessibleName("Text to Speech tab")
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(22)

        control_column = QVBoxLayout()
        control_column.setSpacing(16)

        left = SectionCard()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(22, 22, 22, 22)
        left_layout.setSpacing(14)
        header = QLabel("Session Setup")
        header.setProperty("role", "section-title")
        helper = QLabel("Choose the voice, model and delivery format here. Keep the editor focused on the script.")
        helper.setProperty("role", "muted")
        helper.setWordWrap(True)

        self.active_voice_summary = QLabel("No voice selected.")
        self.active_voice_summary.setProperty("role", "muted")
        self.active_voice_summary.setWordWrap(True)

        self.tts_voice = QComboBox()
        self.tts_voice.setAccessibleName("TTS voice")
        self.tts_voice.currentIndexChanged.connect(self._sync_voice_summary)
        self.tts_voice.currentIndexChanged.connect(self._update_tts_button_state)
        self.tts_model = QComboBox()
        self.tts_model.setAccessibleName("TTS model")
        self.tts_model.currentIndexChanged.connect(self._update_tts_button_state)
        self.tts_model.currentIndexChanged.connect(self._sync_language_options_for_model)
        self.tts_language = QComboBox()
        self.tts_language.setEditable(True)
        self.tts_language.setInsertPolicy(QComboBox.NoInsert)
        self.tts_language.setAccessibleName("Language code")
        self.tts_language.setAccessibleDescription(
            "Optional language code. Use Auto to let the model decide."
        )
        self._populate_language_options([])
        self.tts_output = QComboBox()
        self.tts_output.addItems(OUTPUT_FORMATS)
        self.tts_output.setAccessibleName("TTS output format")
        self.tts_seed = QSpinBox()
        self.tts_seed.setRange(0, 999999)
        self.tts_seed.setSpecialValueText("Auto")
        self.tts_seed.setAccessibleName("TTS seed")
        self.tts_logging = QCheckBox("Enable logging")
        self.tts_logging.setChecked(True)
        self.tts_text = QTextEdit()
        self.tts_text.setPlaceholderText("Paste or type the script that should be synthesized...")
        self.tts_text.setMinimumHeight(360)
        self.tts_text.textChanged.connect(self._update_tts_button_state)
        self.tts_text.textChanged.connect(self._update_tts_text_meta)
        configure_focusable_text_edit(
            self.tts_text,
            name="Text to speech input",
            description="Main TTS script editor. Press Tab to move to Generate Speech.",
        )

        left_layout.addWidget(header)
        left_layout.addWidget(helper)
        left_layout.addWidget(self.active_voice_summary)
        config_form = QFormLayout()
        config_form.setHorizontalSpacing(14)
        config_form.setVerticalSpacing(12)
        for label_text, widget in (
            ("&Voice", self.tts_voice),
            ("&Model", self.tts_model),
            ("&Language code", self.tts_language),
            ("Output &format", self.tts_output),
            ("See&d", self.tts_seed),
        ):
            label = QLabel(label_text)
            label.setBuddy(widget)
            config_form.addRow(label, widget)
        left_layout.addLayout(config_form)
        left_layout.addWidget(self.tts_logging)
        self.tts_button = QPushButton("&Generate Speech")
        self.tts_button.setProperty("variant", "primary")
        self.tts_button.clicked.connect(self._emit_tts)
        left_layout.addWidget(self.tts_button)

        self.tts_settings = VoiceSettingsEditor("Voice Usage Settings")
        self.tts_settings.setAccessibleName("TTS voice usage settings")
        self.tts_advanced = CollapsibleSection(
            "Advanced Voice Settings",
            "Open this only when you need to tune similarity, expressive style or speed.",
            expanded=False,
        )
        self.tts_advanced.content_layout.addWidget(self.tts_settings)

        compose_card = SectionCard()
        compose_layout = QVBoxLayout(compose_card)
        compose_layout.setContentsMargins(24, 24, 24, 24)
        compose_layout.setSpacing(14)
        compose_title = QLabel("Script")
        compose_title.setProperty("role", "section-title")
        compose_subtitle = QLabel(
            "Write or paste the final narration here. Keep the copy clean and let advanced controls stay out of the way."
        )
        compose_subtitle.setProperty("role", "muted")
        compose_subtitle.setWordWrap(True)
        text_label = QLabel("&Text")
        text_label.setBuddy(self.tts_text)
        self.tts_text_meta = QLabel("No script yet.")
        self.tts_text_meta.setProperty("role", "muted")
        compose_layout.addWidget(compose_title)
        compose_layout.addWidget(compose_subtitle)
        compose_layout.addWidget(text_label)
        compose_layout.addWidget(self.tts_text, 1)
        compose_layout.addWidget(self.tts_text_meta)

        control_column.addWidget(left)
        control_column.addWidget(self.tts_advanced)
        control_column.addStretch(1)
        layout.addLayout(control_column, 2)
        layout.addWidget(compose_card, 3)
        defer_tab_order_chain(
            tab,
            self.tabs.tabBar(),
            self.tts_voice,
            self.tts_model,
            self.tts_language,
            self.tts_output,
            self.tts_seed,
            self.tts_logging,
            self.tts_button,
            self.tts_advanced.toggle_button,
            self.tts_text,
            self.tts_settings.stability.slider,
            self.tts_settings.similarity.slider,
            self.tts_settings.style.slider,
            self.tts_settings.speed.slider,
            self.tts_settings.speaker_boost,
        )
        self._update_tts_text_meta()
        return tab

    def _build_sts_tab(self) -> QWidget:
        tab = QWidget()
        tab.setAccessibleName("Speech to Speech tab")
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(22)

        control_column = QVBoxLayout()
        control_column.setSpacing(16)

        left = SectionCard()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(22, 22, 22, 22)
        left_layout.setSpacing(14)
        header = QLabel("Conversion Setup")
        header.setProperty("role", "section-title")
        helper = QLabel("Pick a source clip and destination voice here. The source overview stays separate so the flow feels lighter.")
        helper.setProperty("role", "muted")
        helper.setWordWrap(True)

        self.sts_voice = QComboBox()
        self.sts_voice.setAccessibleName("STS voice")
        self.sts_voice.currentIndexChanged.connect(self._update_sts_button_state)
        self.sts_model = QComboBox()
        self.sts_model.setAccessibleName("STS model")
        self.sts_model.currentIndexChanged.connect(self._update_sts_button_state)
        self.sts_output = QComboBox()
        self.sts_output.addItems(OUTPUT_FORMATS)
        self.sts_output.setAccessibleName("STS output format")
        self.sts_seed = QSpinBox()
        self.sts_seed.setRange(0, 999999)
        self.sts_seed.setSpecialValueText("Auto")
        self.sts_seed.setAccessibleName("STS seed")
        self.sts_logging = QCheckBox("Enable logging")
        self.sts_logging.setChecked(True)
        self.sts_file = QLineEdit()
        self.sts_file.setReadOnly(True)
        self.sts_file.setPlaceholderText("Select a source audio file")
        self.sts_file.setAccessibleName("Speech to speech source file")
        self.pick_button = QPushButton("&Browse Audio")
        self.pick_button.setIcon(build_icon("upload"))
        self.pick_button.clicked.connect(self._pick_sts_file)
        file_row = QHBoxLayout()
        file_row.addWidget(self.sts_file, 1)
        file_row.addWidget(self.pick_button)

        left_layout.addWidget(header)
        left_layout.addWidget(helper)
        config_form = QFormLayout()
        config_form.setHorizontalSpacing(14)
        config_form.setVerticalSpacing(12)
        input_label = QLabel("Input &audio")
        input_label.setBuddy(self.sts_file)
        config_form.addRow(input_label, file_row)
        for label_text, widget in (
            ("V&oice", self.sts_voice),
            ("Mo&del", self.sts_model),
            ("Output f&ormat", self.sts_output),
            ("Se&ed", self.sts_seed),
        ):
            label = QLabel(label_text)
            label.setBuddy(widget)
            config_form.addRow(label, widget)
        left_layout.addLayout(config_form)
        left_layout.addWidget(self.sts_logging)
        self.sts_button = QPushButton("Con&vert Voice")
        self.sts_button.setProperty("variant", "primary")
        self.sts_button.clicked.connect(self._emit_sts)
        left_layout.addWidget(self.sts_button)

        self.sts_settings = VoiceSettingsEditor("Conversion Settings")
        self.sts_settings.setAccessibleName("Speech to speech conversion settings")
        self.sts_advanced = CollapsibleSection(
            "Advanced Conversion Settings",
            "Open when you want to steer timbre similarity, style or pace during conversion.",
            expanded=False,
        )
        self.sts_advanced.content_layout.addWidget(self.sts_settings)

        source_card = SectionCard()
        source_layout = QVBoxLayout(source_card)
        source_layout.setContentsMargins(24, 24, 24, 24)
        source_layout.setSpacing(14)
        source_title = QLabel("Source Audio")
        source_title.setProperty("role", "section-title")
        source_subtitle = QLabel(
            "Keep an eye on the selected clip and replace it whenever you want a cleaner conversion input."
        )
        source_subtitle.setProperty("role", "muted")
        source_subtitle.setWordWrap(True)
        self.sts_source_summary = QLabel("No source audio selected.")
        self.sts_source_summary.setProperty("role", "muted")
        self.sts_source_summary.setWordWrap(True)
        source_layout.addWidget(source_title)
        source_layout.addWidget(source_subtitle)
        source_layout.addWidget(self.sts_source_summary)
        source_layout.addStretch(1)

        control_column.addWidget(left)
        control_column.addWidget(self.sts_advanced)
        control_column.addStretch(1)
        layout.addLayout(control_column, 2)
        layout.addWidget(source_card, 3)
        defer_tab_order_chain(
            tab,
            self.sts_file,
            self.pick_button,
            self.sts_voice,
            self.sts_model,
            self.sts_output,
            self.sts_seed,
            self.sts_logging,
            self.sts_button,
            self.sts_advanced.toggle_button,
            self.sts_settings.stability.slider,
            self.sts_settings.similarity.slider,
            self.sts_settings.style.slider,
            self.sts_settings.speed.slider,
            self.sts_settings.speaker_boost,
        )
        self._update_sts_source_summary()
        return tab

    def set_voice_options(self, voices: list[dict]) -> None:
        self._voices_by_id = {voice.get("voice_id", ""): voice for voice in voices if voice.get("voice_id")}
        current_tts = self.tts_voice.currentData()
        current_sts = self.sts_voice.currentData()
        self.tts_voice.clear()
        self.sts_voice.clear()
        for voice in voices:
            label = f"{voice.get('name', 'Unknown')}  [{voice.get('category', 'n/a')}]"
            voice_id = voice.get("voice_id", "")
            self.tts_voice.addItem(label, voice_id)
            self.sts_voice.addItem(label, voice_id)
        self._restore_combo(self.tts_voice, current_tts)
        self._restore_combo(self.sts_voice, current_sts)
        self._sync_voice_summary()
        self._update_tts_button_state()
        self._update_sts_button_state()

    def set_model_options(self, models: list[dict]) -> None:
        self._models_by_id = {model.get("model_id", ""): model for model in models if model.get("model_id")}
        current_tts = self.tts_model.currentData()
        current_sts = self.sts_model.currentData()
        self.tts_model.clear()
        self.sts_model.clear()
        for model in models:
            model_id = model.get("model_id", "")
            name = model.get("name", model_id)
            if model.get("can_do_text_to_speech"):
                self.tts_model.addItem(name, model_id)
            if model.get("can_do_voice_conversion"):
                self.sts_model.addItem(name, model_id)
        self._restore_combo(self.tts_model, current_tts)
        self._restore_combo(self.sts_model, current_sts)
        self._sync_language_options_for_model()
        self._update_tts_button_state()
        self._update_sts_button_state()

    def route_voice(self, voice: dict) -> None:
        voice_id = voice.get("voice_id", "")
        if not voice_id:
            return
        self.tabs.setCurrentIndex(0)
        self._restore_combo(self.tts_voice, voice_id)
        self._restore_combo(self.sts_voice, voice_id)
        self._sync_voice_summary()
        self.context_status.setText(
            f"{voice.get('name', 'Unknown')} Studio akisina tasindi. Metni yapistirip Generate Speech dugmesine basabilirsin."
        )
        self.tts_text.setFocus()
        self._update_tts_text_meta()

    def set_result(self, title: str, meta: str) -> None:
        self.result_card.set_result(title, meta, can_open_folder=True)

    def clear_result(self) -> None:
        self.result_card.clear()

    def show_status(self, message: str) -> None:
        self.context_status.setText(message)

    def _restore_combo(self, combo: QComboBox, value: str | None) -> None:
        if not value:
            return
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _pick_sts_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select source audio",
            "",
            "Audio Files (*.mp3 *.wav *.m4a *.flac *.ogg)",
        )
        if not file_name:
            return
        self.sts_audio_path = Path(file_name)
        self.sts_file.setText(file_name)
        self._update_sts_source_summary()
        self._update_sts_button_state()

    def _sync_voice_summary(self) -> None:
        voice = self._voices_by_id.get(self.tts_voice.currentData() or "")
        if not voice:
            self.active_voice_summary.setText("No voice selected.")
            return
        fine_tuning = voice.get("fine_tuning") or {}
        pieces = [
            voice.get("name", "Unknown"),
            f"type: {voice.get('category', 'n/a')}",
        ]
        if fine_tuning.get("language"):
            pieces.append(f"language: {fine_tuning.get('language')}")
        self.active_voice_summary.setText(" | ".join(pieces))

    def _update_tts_text_meta(self) -> None:
        text = self.tts_text.toPlainText().strip()
        if not text:
            self.tts_text_meta.setText("No script yet.")
            return
        words = len(text.split())
        chars = len(text)
        self.tts_text_meta.setText(f"{words} words | {chars} characters")

    def _update_sts_source_summary(self) -> None:
        if not self.sts_audio_path:
            self.sts_source_summary.setText("No source audio selected.")
            return
        self.sts_source_summary.setText(
            f"{self.sts_audio_path.name} | folder: {self.sts_audio_path.parent}"
        )

    def _update_tts_button_state(self) -> None:
        enabled = bool(self.tts_voice.currentData() and self.tts_model.currentData() and self.tts_text.toPlainText().strip())
        self.tts_button.setEnabled(enabled)

    def selected_language_code(self) -> str:
        text = self.tts_language.currentText().strip().lower()
        if text in {"", "auto"}:
            return ""
        return text

    def _update_sts_button_state(self) -> None:
        enabled = bool(self.sts_voice.currentData() and self.sts_model.currentData() and self.sts_audio_path)
        self.sts_button.setEnabled(enabled)

    def _emit_tts(self) -> None:
        self.tts_requested.emit(
            {
                "voice_id": self.tts_voice.currentData(),
                "model_id": self.tts_model.currentData(),
                "text": self.tts_text.toPlainText().strip(),
                "language_code": self.selected_language_code(),
                "output_format": self.tts_output.currentText(),
                "seed": self.tts_seed.value() or None,
                "enable_logging": self.tts_logging.isChecked(),
                "voice_settings": self.tts_settings.settings(),
            }
        )

    def _populate_language_options(self, codes: list[str]) -> None:
        current = self.selected_language_code()
        self.tts_language.blockSignals(True)
        self.tts_language.clear()
        self.tts_language.addItem("Auto", "")
        seen = {""}
        for code in codes + COMMON_LANGUAGE_CODES:
            value = str(code).strip().lower()
            if not value or value in seen:
                continue
            seen.add(value)
            self.tts_language.addItem(value, value)
        if current:
            index = self.tts_language.findData(current)
            if index >= 0:
                self.tts_language.setCurrentIndex(index)
            else:
                self.tts_language.setEditText(current)
        else:
            self.tts_language.setCurrentIndex(0)
        self.tts_language.blockSignals(False)

    def _sync_language_options_for_model(self) -> None:
        model = self._models_by_id.get(self.tts_model.currentData() or "", {})
        raw_languages = model.get("languages")
        model_codes: list[str] = []
        if isinstance(raw_languages, list):
            for item in raw_languages:
                if isinstance(item, dict):
                    code = item.get("language_id") or item.get("code") or item.get("id")
                    if code:
                        model_codes.append(str(code))
                elif isinstance(item, str):
                    model_codes.append(item)
        self._populate_language_options(model_codes)

    def _emit_sts(self) -> None:
        self.sts_requested.emit(
            {
                "voice_id": self.sts_voice.currentData(),
                "model_id": self.sts_model.currentData(),
                "audio_path": str(self.sts_audio_path) if self.sts_audio_path else "",
                "output_format": self.sts_output.currentText(),
                "seed": self.sts_seed.value() or None,
                "enable_logging": self.sts_logging.isChecked(),
                "voice_settings": self.sts_settings.settings(),
            }
        )
