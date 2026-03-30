from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QWidget

from eleven_gui.accessibility import set_tab_order_chain
from eleven_gui.ui.widgets import SectionCard, build_icon


class SettingsPage(QWidget):
    save_requested = Signal(str)
    test_requested = Signal(str)
    spoken_fallback_toggled = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.setAccessibleName("Settings page")
        self.setAccessibleDescription("Manage the ElevenLabs API key and open official documentation links.")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title = QLabel("Settings")
        title.setProperty("role", "title")
        subtitle = QLabel("Keep connection settings, fallback behavior and official references in one quieter place.")
        subtitle.setProperty("role", "muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(18)

        card = SectionCard()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 22, 22, 22)
        card_layout.setSpacing(12)

        key_label = QLabel("&ElevenLabs API Key")
        key_label.setProperty("role", "section-title")
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setPlaceholderText("Paste your ElevenLabs API key")
        self.key_input.setAccessibleName("ElevenLabs API key")
        key_label.setBuddy(self.key_input)
        self.source_label = QLabel("Source: missing")
        self.source_label.setProperty("role", "muted")
        self.status_label = QLabel("No connection test run yet.")
        self.status_label.setProperty("role", "muted")
        self.spoken_fallback = QCheckBox("Use spoken fallback when no screen reader is active")
        self.spoken_fallback.setAccessibleName("Spoken fallback")
        self.spoken_fallback.toggled.connect(self.spoken_fallback_toggled.emit)

        self.save_button = QPushButton("&Save to .env")
        self.save_button.setProperty("variant", "primary")
        self.save_button.setIcon(build_icon("save"))
        self.save_button.clicked.connect(lambda: self.save_requested.emit(self.key_input.text().strip()))
        self.test_button = QPushButton("&Test Connection")
        self.test_button.setIcon(build_icon("refresh"))
        self.test_button.clicked.connect(lambda: self.test_requested.emit(self.key_input.text().strip()))

        docs_card = SectionCard()
        docs_layout = QVBoxLayout(docs_card)
        docs_layout.setContentsMargins(22, 22, 22, 22)
        docs_layout.setSpacing(12)
        docs_title = QLabel("Official References")
        docs_title.setProperty("role", "section-title")
        docs_intro = QLabel("Open the endpoints you use most often when you need to verify payloads, limits or behavior.")
        docs_intro.setProperty("role", "muted")
        docs_intro.setWordWrap(True)
        docs = QLabel(
            '<a href="https://elevenlabs.io/docs/api-reference/user/subscription/get">Subscription</a> | '
            '<a href="https://elevenlabs.io/docs/api-reference/voices/search">Voices</a> | '
            '<a href="https://elevenlabs.io/docs/api-reference/text-to-speech/convert">TTS</a> | '
            '<a href="https://elevenlabs.io/docs/api-reference/speech-to-speech/convert">STS</a> | '
            '<a href="https://elevenlabs.io/docs/api-reference/history/get-all">History</a>'
        )
        docs.setOpenExternalLinks(True)

        card_layout.addWidget(key_label)
        card_layout.addWidget(self.key_input)
        card_layout.addWidget(self.source_label)
        card_layout.addWidget(self.status_label)
        card_layout.addWidget(self.spoken_fallback)
        card_layout.addWidget(self.save_button)
        card_layout.addWidget(self.test_button)
        card_layout.addStretch(1)

        docs_layout.addWidget(docs_title)
        docs_layout.addWidget(docs_intro)
        docs_layout.addWidget(docs)
        docs_layout.addStretch(1)

        body.addWidget(card, 3)
        body.addWidget(docs_card, 2)

        layout.addLayout(body)
        layout.addStretch(1)
        self.initial_focus_widget = self.key_input
        set_tab_order_chain(self.key_input, self.spoken_fallback, self.save_button, self.test_button)

    def set_api_state(self, *, key_value: str, source: str, status: str, spoken_fallback: bool = False) -> None:
        self.key_input.setText(key_value)
        self.source_label.setText(f"Source: {source}")
        self.status_label.setText(status)
        self.spoken_fallback.setChecked(spoken_fallback)
