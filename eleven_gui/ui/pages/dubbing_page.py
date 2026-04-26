from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
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
    QVBoxLayout,
    QWidget,
)

from eleven_gui.accessibility import defer_tab_order_chain
from eleven_gui.ui.widgets import AccessibleListWidget, MetricCard, SectionCard, build_icon


class DubbingPage(QWidget):
    refresh_requested = Signal(object)
    create_requested = Signal(object)
    load_requested = Signal(str)
    download_requested = Signal(object)
    delete_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._dubs: list[dict] = []
        self._source_file: Path | None = None

        self.setAccessibleName("Dubbing page")
        self.setAccessibleDescription("Create and manage dubbing jobs from file uploads or source URLs.")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title = QLabel("Dubbing")
        title.setProperty("role", "title")
        subtitle = QLabel(
            "Translate audio or video to another language. Upload a file or use a source URL, then track and download results."
        )
        subtitle.setProperty("role", "muted")
        subtitle.setWordWrap(True)
        self.page_status = QLabel("Ready for a new dubbing task.")
        self.page_status.setProperty("role", "muted")
        self.page_status.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.page_status)

        metrics = QHBoxLayout()
        metrics.setSpacing(14)
        self.total_card = MetricCard("Dubs", "0", "Loaded dubbing tasks")
        self.selected_card = MetricCard("Selection", "0", "No dubbing selected")
        metrics.addWidget(self.total_card)
        metrics.addWidget(self.selected_card)
        layout.addLayout(metrics)

        body = QHBoxLayout()
        body.setSpacing(14)

        create_card = SectionCard()
        create_layout = QVBoxLayout(create_card)
        create_layout.setContentsMargins(18, 18, 18, 18)
        create_layout.setSpacing(12)
        create_title = QLabel("Create Dub")
        create_title.setProperty("role", "section-title")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Optional dubbing name")
        self.target_lang = QComboBox()
        self.target_lang.setEditable(True)
        self.target_lang.addItems(["tr", "en", "es", "de", "fr", "it", "pt", "ar", "ja"])
        self.source_lang = QComboBox()
        self.source_lang.setEditable(True)
        self.source_lang.addItems(["auto", "tr", "en", "es", "de", "fr", "it", "pt", "ar", "ja"])
        self.source_url = QLineEdit()
        self.source_url.setPlaceholderText("https://...")
        self.source_file = QLineEdit()
        self.source_file.setReadOnly(True)
        self.source_file.setPlaceholderText("Or choose a local file")
        self.pick_file_button = QPushButton("Browse &File")
        self.pick_file_button.setIcon(build_icon("upload"))
        self.pick_file_button.clicked.connect(self._pick_source_file)
        file_row = QHBoxLayout()
        file_row.setContentsMargins(0, 0, 0, 0)
        file_row.setSpacing(8)
        file_row.addWidget(self.source_file, 1)
        file_row.addWidget(self.pick_file_button)

        self.num_speakers = QSpinBox()
        self.num_speakers.setRange(0, 20)
        self.watermark = QCheckBox("Use watermark when available")
        self.highest_resolution = QCheckBox("Use highest resolution")
        self.drop_background = QCheckBox("Drop background audio")
        self.profanity_filter = QCheckBox("Use profanity filter")
        self.create_button = QPushButton("&Create Dub")
        self.create_button.setProperty("variant", "primary")
        self.create_button.clicked.connect(self._emit_create)

        form = QFormLayout()
        form.addRow("&Name", self.name_input)
        form.addRow("&Target language", self.target_lang)
        form.addRow("&Source language", self.source_lang)
        form.addRow("Source &URL", self.source_url)
        form.addRow("Source &file", file_row)
        form.addRow("&Speakers", self.num_speakers)

        create_layout.addWidget(create_title)
        create_layout.addLayout(form)
        create_layout.addWidget(self.watermark)
        create_layout.addWidget(self.highest_resolution)
        create_layout.addWidget(self.drop_background)
        create_layout.addWidget(self.profanity_filter)
        create_layout.addWidget(self.create_button)
        create_layout.addStretch(1)

        list_card = SectionCard()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(18, 18, 18, 18)
        list_layout.setSpacing(12)
        list_title = QLabel("Dubbing Jobs")
        list_title.setProperty("role", "section-title")
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        self.status_filter = QComboBox()
        self.status_filter.addItem("All statuses", "")
        self.status_filter.addItem("Dubbing", "dubbing")
        self.status_filter.addItem("Dubbed", "dubbed")
        self.status_filter.addItem("Failed", "failed")
        self.refresh_button = QPushButton("&Refresh")
        self.refresh_button.setIcon(build_icon("refresh"))
        self.refresh_button.clicked.connect(self._emit_refresh)
        toolbar.addWidget(self.status_filter)
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch(1)

        self.list_widget = AccessibleListWidget("Dubbing jobs list", multi_select=True)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)

        self.detail_label = QLabel("Select a dubbing job to see details.")
        self.detail_label.setProperty("role", "muted")
        self.detail_label.setWordWrap(True)
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(8)
        self.language_download = QLineEdit("tr")
        self.language_download.setPlaceholderText("Language code")
        self.download_button = QPushButton("&Download")
        self.download_button.setIcon(build_icon("download"))
        self.download_button.clicked.connect(self._emit_download)
        self.delete_button = QPushButton("&Delete Selected")
        self.delete_button.setProperty("variant", "danger")
        self.delete_button.clicked.connect(self._emit_delete)
        action_row.addWidget(self.language_download)
        action_row.addWidget(self.download_button)
        action_row.addWidget(self.delete_button)
        action_row.addStretch(1)

        list_layout.addWidget(list_title)
        list_layout.addLayout(toolbar)
        list_layout.addWidget(self.list_widget, 1)
        list_layout.addWidget(self.detail_label)
        list_layout.addLayout(action_row)

        body.addWidget(create_card, 3)
        body.addWidget(list_card, 4)
        layout.addLayout(body, 1)

        self.initial_focus_widget = self.name_input
        defer_tab_order_chain(
            self,
            self.name_input,
            self.target_lang,
            self.source_lang,
            self.source_url,
            self.source_file,
            self.pick_file_button,
            self.num_speakers,
            self.watermark,
            self.highest_resolution,
            self.drop_background,
            self.profanity_filter,
            self.create_button,
            self.status_filter,
            self.refresh_button,
            self.list_widget,
            self.language_download,
            self.download_button,
            self.delete_button,
        )
        self._update_actions()

    def set_dubs(self, payload: dict) -> None:
        self._dubs = payload.get("dubs", [])
        self.total_card.set_content(str(len(self._dubs)), "Loaded dubbing tasks")
        items = [self._item_text(item) for item in self._dubs]
        self.list_widget.set_items(items)
        self._update_actions()

    def show_status(self, message: str) -> None:
        self.page_status.setText(message)

    def _pick_source_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Choose source media",
            "",
            "Media files (*.mp4 *.mov *.mkv *.mp3 *.wav *.m4a *.aac *.ogg *.flac);;All files (*.*)",
        )
        if not file_name:
            return
        self._source_file = Path(file_name)
        self.source_file.setText(file_name)

    def _selected_dubs(self) -> list[dict]:
        return [self._dubs[row] for row in self.list_widget.selected_rows() if 0 <= row < len(self._dubs)]

    def _primary_dub(self) -> dict | None:
        selected = self._selected_dubs()
        return selected[0] if selected else None

    def _item_text(self, dub: dict) -> str:
        targets = ", ".join(dub.get("target_languages", []) or [])
        return " | ".join(
            [
                dub.get("name", "Unnamed Dub"),
                f"status: {dub.get('status', 'unknown')}",
                f"targets: {targets or 'n/a'}",
                dub.get("dubbing_id", ""),
            ]
        )

    def _on_selection_changed(self) -> None:
        selected = self._selected_dubs()
        self.selected_card.set_content(str(len(selected)), "Selected dubbing jobs")
        if not selected:
            self.detail_label.setText("Select a dubbing job to see details.")
            self._update_actions()
            return
        first = selected[0]
        targets = first.get("target_languages", []) or []
        if targets:
            self.language_download.setText(targets[0])
        detail = [
            first.get("name", "Unnamed Dub"),
            f"id: {first.get('dubbing_id', '')}",
            f"status: {first.get('status', 'unknown')}",
            f"source: {first.get('source_language', 'n/a')}",
            f"targets: {', '.join(targets) if targets else 'n/a'}",
        ]
        if len(selected) > 1:
            detail.append(f"{len(selected)} jobs selected. Download uses first selected job.")
        self.detail_label.setText(" | ".join(detail))
        self.load_requested.emit(first.get("dubbing_id", ""))
        self._update_actions()

    def _update_actions(self) -> None:
        selected = self._selected_dubs()
        has_selection = bool(selected)
        self.download_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def _emit_refresh(self) -> None:
        self.refresh_requested.emit(
            {
                "dubbing_status": self.status_filter.currentData() or "",
            }
        )

    def _emit_create(self) -> None:
        self.create_requested.emit(
            {
                "name": self.name_input.text().strip(),
                "target_lang": self.target_lang.currentText().strip(),
                "source_lang": self.source_lang.currentText().strip() or "auto",
                "source_url": self.source_url.text().strip(),
                "file_path": str(self._source_file) if self._source_file else "",
                "num_speakers": int(self.num_speakers.value()),
                "watermark": self.watermark.isChecked(),
                "highest_resolution": self.highest_resolution.isChecked(),
                "drop_background_audio": self.drop_background.isChecked(),
                "use_profanity_filter": self.profanity_filter.isChecked(),
            }
        )

    def _emit_download(self) -> None:
        dub = self._primary_dub()
        if not dub:
            return
        self.download_requested.emit(
            {
                "dubbing_id": dub.get("dubbing_id", ""),
                "language_code": self.language_download.text().strip(),
            }
        )

    def _emit_delete(self) -> None:
        ids = [dub.get("dubbing_id", "") for dub in self._selected_dubs() if dub.get("dubbing_id")]
        if ids:
            self.delete_requested.emit(ids if len(ids) > 1 else ids[0])
