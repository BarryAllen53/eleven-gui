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
    QVBoxLayout,
    QWidget,
)

from eleven_gui.accessibility import defer_tab_order_chain
from eleven_gui.ui.widgets import AccessibleListWidget, MetricCard, SectionCard, build_icon


class ProjectsPage(QWidget):
    refresh_requested = Signal()
    create_requested = Signal(object)
    load_requested = Signal(str)
    convert_requested = Signal(str)
    download_requested = Signal(str)
    delete_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._projects: list[dict] = []
        self._document_path: Path | None = None

        self.setAccessibleName("Audiobooks page")
        self.setAccessibleDescription("Manage ElevenLabs Studio projects and audiobook exports.")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title = QLabel("Audiobooks")
        title.setProperty("role", "title")
        subtitle = QLabel(
            "Create Studio projects from files or URLs, run conversion, and download final audio archives."
        )
        subtitle.setProperty("role", "muted")
        subtitle.setWordWrap(True)
        self.page_status = QLabel("Ready for Studio projects.")
        self.page_status.setProperty("role", "muted")
        self.page_status.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.page_status)

        metrics = QHBoxLayout()
        metrics.setSpacing(14)
        self.total_card = MetricCard("Projects", "0", "Studio projects loaded")
        self.selection_card = MetricCard("Selection", "0", "No project selected")
        metrics.addWidget(self.total_card)
        metrics.addWidget(self.selection_card)
        layout.addLayout(metrics)

        body = QHBoxLayout()
        body.setSpacing(14)

        create_card = SectionCard()
        create_layout = QVBoxLayout(create_card)
        create_layout.setContentsMargins(18, 18, 18, 18)
        create_layout.setSpacing(12)
        create_title = QLabel("Create Project")
        create_title.setProperty("role", "section-title")

        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("Project name")
        self.from_url = QLineEdit()
        self.from_url.setPlaceholderText("Optional source URL")
        self.default_model = QComboBox()
        self.default_title_voice = QComboBox()
        self.default_paragraph_voice = QComboBox()
        self.quality_preset = QComboBox()
        self.quality_preset.addItem("Default", "")
        self.quality_preset.addItem("Standard", "standard")
        self.quality_preset.addItem("High", "high")
        self.quality_preset.addItem("Ultra", "ultra")
        self.quality_preset.addItem("Ultra lossless", "ultra_lossless")
        self.auto_convert = QCheckBox("Auto convert after creation")
        self.document_path = QLineEdit()
        self.document_path.setReadOnly(True)
        self.document_path.setPlaceholderText("Optional document file (EPUB, PDF, DOCX, TXT...)")
        self.pick_document_button = QPushButton("Browse &Document")
        self.pick_document_button.setIcon(build_icon("upload"))
        self.pick_document_button.clicked.connect(self._pick_document)
        doc_row = QHBoxLayout()
        doc_row.setContentsMargins(0, 0, 0, 0)
        doc_row.setSpacing(8)
        doc_row.addWidget(self.document_path, 1)
        doc_row.addWidget(self.pick_document_button)

        form = QFormLayout()
        form.addRow("&Name", self.project_name)
        form.addRow("From &URL", self.from_url)
        form.addRow("&Model", self.default_model)
        form.addRow("Title v&oice", self.default_title_voice)
        form.addRow("&Paragraph voice", self.default_paragraph_voice)
        form.addRow("&Quality preset", self.quality_preset)
        form.addRow("&Document", doc_row)

        self.create_button = QPushButton("&Create Project")
        self.create_button.setProperty("variant", "primary")
        self.create_button.clicked.connect(self._emit_create)

        create_layout.addWidget(create_title)
        create_layout.addLayout(form)
        create_layout.addWidget(self.auto_convert)
        create_layout.addWidget(self.create_button)
        create_layout.addStretch(1)

        list_card = SectionCard()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(18, 18, 18, 18)
        list_layout.setSpacing(12)
        list_title = QLabel("Studio Projects")
        list_title.setProperty("role", "section-title")
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        self.refresh_button = QPushButton("&Refresh")
        self.refresh_button.setIcon(build_icon("refresh"))
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch(1)

        self.list_widget = AccessibleListWidget("Studio projects list", multi_select=True)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)

        self.detail_label = QLabel("Select a project to inspect details.")
        self.detail_label.setProperty("role", "muted")
        self.detail_label.setWordWrap(True)
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)
        self.convert_button = QPushButton("&Convert Project")
        self.convert_button.clicked.connect(self._emit_convert)
        self.download_button = QPushButton("&Download Archive")
        self.download_button.setIcon(build_icon("download"))
        self.download_button.clicked.connect(self._emit_download)
        self.delete_button = QPushButton("&Delete Selected")
        self.delete_button.setProperty("variant", "danger")
        self.delete_button.clicked.connect(self._emit_delete)
        actions.addWidget(self.convert_button)
        actions.addWidget(self.download_button)
        actions.addWidget(self.delete_button)
        actions.addStretch(1)

        list_layout.addWidget(list_title)
        list_layout.addLayout(toolbar)
        list_layout.addWidget(self.list_widget, 1)
        list_layout.addWidget(self.detail_label)
        list_layout.addLayout(actions)

        body.addWidget(create_card, 3)
        body.addWidget(list_card, 4)
        layout.addLayout(body, 1)

        self.initial_focus_widget = self.project_name
        defer_tab_order_chain(
            self,
            self.project_name,
            self.from_url,
            self.default_model,
            self.default_title_voice,
            self.default_paragraph_voice,
            self.quality_preset,
            self.document_path,
            self.pick_document_button,
            self.auto_convert,
            self.create_button,
            self.refresh_button,
            self.list_widget,
            self.convert_button,
            self.download_button,
            self.delete_button,
        )
        self._update_actions()

    def set_voice_options(self, voices: list[dict]) -> None:
        current_title = self.default_title_voice.currentData()
        current_paragraph = self.default_paragraph_voice.currentData()
        self.default_title_voice.clear()
        self.default_paragraph_voice.clear()
        self.default_title_voice.addItem("Default voice", "")
        self.default_paragraph_voice.addItem("Default voice", "")
        for voice in voices:
            voice_id = voice.get("voice_id", "")
            if not voice_id:
                continue
            label = f"{voice.get('name', 'Unknown')} [{voice.get('category', 'n/a')}]"
            self.default_title_voice.addItem(label, voice_id)
            self.default_paragraph_voice.addItem(label, voice_id)
        self._restore_combo(self.default_title_voice, current_title)
        self._restore_combo(self.default_paragraph_voice, current_paragraph)

    def set_model_options(self, models: list[dict]) -> None:
        current = self.default_model.currentData()
        self.default_model.clear()
        self.default_model.addItem("Default model", "")
        for model in models:
            model_id = model.get("model_id", "")
            if not model_id:
                continue
            self.default_model.addItem(model.get("name", model_id), model_id)
        self._restore_combo(self.default_model, current)

    def set_projects(self, projects: list[dict]) -> None:
        self._projects = projects
        self.total_card.set_content(str(len(projects)), "Studio projects loaded")
        self.list_widget.set_items([self._item_text(project) for project in projects])
        self._update_actions()

    def show_status(self, message: str) -> None:
        self.page_status.setText(message)

    def set_project_detail(self, detail: dict, snapshots: list[dict]) -> None:
        if not detail:
            self.detail_label.setText("Select a project to inspect details.")
            return
        self.detail_label.setText(
            " | ".join(
                [
                    detail.get("name", "Unnamed project"),
                    f"id: {detail.get('project_id', '')}",
                    f"state: {detail.get('state', 'unknown')}",
                    f"chapters: {len(detail.get('chapters', []) or [])}",
                    f"snapshots: {len(snapshots)}",
                    f"downloadable: {'yes' if detail.get('can_be_downloaded') else 'no'}",
                ]
            )
        )

    def _restore_combo(self, combo: QComboBox, value: str | None) -> None:
        if not value:
            return
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _pick_document(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Choose document",
            "",
            "Documents (*.epub *.pdf *.docx *.txt *.md *.html *.htm);;All files (*.*)",
        )
        if not file_name:
            return
        self._document_path = Path(file_name)
        self.document_path.setText(file_name)

    def _selected_projects(self) -> list[dict]:
        return [self._projects[row] for row in self.list_widget.selected_rows() if 0 <= row < len(self._projects)]

    def _primary_project(self) -> dict | None:
        selected = self._selected_projects()
        return selected[0] if selected else None

    def _item_text(self, project: dict) -> str:
        return " | ".join(
            [
                project.get("name", "Unnamed project"),
                f"state: {project.get('state', 'unknown')}",
                f"id: {project.get('project_id', '')}",
            ]
        )

    def _on_selection_changed(self) -> None:
        selected = self._selected_projects()
        self.selection_card.set_content(str(len(selected)), "Selected projects")
        if not selected:
            self.detail_label.setText("Select a project to inspect details.")
            self._update_actions()
            return
        first = selected[0]
        if len(selected) > 1:
            self.detail_label.setText(
                f"{len(selected)} projects selected. Convert and download use the first selected project."
            )
        self.load_requested.emit(first.get("project_id", ""))
        self._update_actions()

    def _update_actions(self) -> None:
        has_selection = bool(self._selected_projects())
        self.convert_button.setEnabled(has_selection)
        self.download_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def _emit_create(self) -> None:
        self.create_requested.emit(
            {
                "name": self.project_name.text().strip(),
                "from_url": self.from_url.text().strip(),
                "from_document_path": str(self._document_path) if self._document_path else "",
                "default_model_id": self.default_model.currentData() or "",
                "default_title_voice_id": self.default_title_voice.currentData() or "",
                "default_paragraph_voice_id": self.default_paragraph_voice.currentData() or "",
                "quality_preset": self.quality_preset.currentData() or "",
                "auto_convert": self.auto_convert.isChecked(),
            }
        )

    def _emit_convert(self) -> None:
        project = self._primary_project()
        if project:
            self.convert_requested.emit(project.get("project_id", ""))

    def _emit_download(self) -> None:
        project = self._primary_project()
        if project:
            self.download_requested.emit(project.get("project_id", ""))

    def _emit_delete(self) -> None:
        ids = [project.get("project_id", "") for project in self._selected_projects() if project.get("project_id")]
        if ids:
            self.delete_requested.emit(ids if len(ids) > 1 else ids[0])
