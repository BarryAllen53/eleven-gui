from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from eleven_gui.accessibility import set_tab_order_chain
from eleven_gui.ui.widgets import AccessibleListWidget, MetricCard, SectionCard, build_icon
from eleven_gui.utils import format_unix


class HistoryPage(QWidget):
    refresh_requested = Signal(object)
    play_requested = Signal(str)
    download_requested = Signal(object)
    delete_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.history_rows: list[dict] = []
        self.setAccessibleName("History page")
        self.setAccessibleDescription("Browse generation history, replay audio, download files, or delete entries.")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title = QLabel("History")
        title.setProperty("role", "title")
        subtitle = QLabel("A lighter history view for replaying, downloading and cleaning up generated audio.")
        subtitle.setProperty("role", "muted")

        self.page_status = QLabel("Select one or more entries to replay the first item, or download and delete in batches.")
        self.page_status.setProperty("role", "muted")
        self.page_status.setWordWrap(True)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(14)
        self.loaded_card = MetricCard("Loaded Items", "0", "History rows in view")
        self.source_card = MetricCard("Source Filter", "All", "No source filter active")
        self.selection_card = MetricCard("Selection", "0", "Nothing selected yet")
        summary_row.addWidget(self.loaded_card)
        summary_row.addWidget(self.source_card)
        summary_row.addWidget(self.selection_card)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search generated items")
        self.search.setAccessibleName("Search history items")
        self.search.setAccessibleDescription("Filters the generation history list.")
        self.source_filter = QComboBox()
        self.source_filter.addItems(["", "TTS", "STS"])
        self.source_filter.setAccessibleName("History source filter")
        self.refresh_button = QPushButton("&Refresh")
        self.refresh_button.setIcon(build_icon("refresh"))
        self.refresh_button.clicked.connect(self._emit_refresh)
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(self.source_filter)
        toolbar.addWidget(self.refresh_button)

        list_card = SectionCard()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(18, 18, 18, 18)
        list_layout.setSpacing(10)
        list_title = QLabel("Generation Items")
        list_title.setProperty("role", "section-title")
        self.list_widget = AccessibleListWidget("Generation history list", multi_select=True)
        self.table = self.list_widget
        self.list_widget.itemSelectionChanged.connect(self._update_selection_state)
        self.detail_label = QLabel("Select a history item to inspect it.")
        self.detail_label.setProperty("role", "muted")
        self.detail_label.setWordWrap(True)
        list_layout.addWidget(list_title)
        list_layout.addWidget(self.list_widget, 1)
        list_layout.addWidget(self.detail_label)

        actions = QHBoxLayout()
        self.play_button = QPushButton("&Play")
        self.play_button.setIcon(build_icon("play"))
        self.play_button.clicked.connect(self._emit_play)
        self.download_button = QPushButton("&Download")
        self.download_button.setIcon(build_icon("download"))
        self.download_button.clicked.connect(self._emit_download)
        self.delete_button = QPushButton("&Delete")
        self.delete_button.setProperty("variant", "danger")
        self.delete_button.setIcon(build_icon("delete"))
        self.delete_button.clicked.connect(self._emit_delete)
        actions.addWidget(self.play_button)
        actions.addWidget(self.download_button)
        actions.addWidget(self.delete_button)
        actions.addStretch(1)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.page_status)
        layout.addLayout(summary_row)
        layout.addLayout(toolbar)
        layout.addWidget(list_card, 1)
        layout.addLayout(actions)
        self.initial_focus_widget = self.search
        set_tab_order_chain(
            self.search,
            self.source_filter,
            self.refresh_button,
            self.list_widget,
            self.play_button,
            self.download_button,
            self.delete_button,
        )
        self._update_selection_state()

    def set_history(self, history_rows: list[dict]) -> None:
        previous_ids = {item.get("history_item_id", "") for item in self._selected_history_items()}
        self.history_rows = history_rows
        self.loaded_card.set_content(str(len(history_rows)), "History rows in view")
        current_source = self.source_filter.currentText().strip() or "All"
        self.source_card.set_content(current_source, "Current source filter")
        rows = [self._item_text(entry) for entry in history_rows]
        selected_rows = [index for index, entry in enumerate(history_rows) if entry.get("history_item_id", "") in previous_ids]
        self.list_widget.set_items(rows, selected_rows=selected_rows)
        self._update_selection_state()

    def current_filters(self) -> dict[str, str]:
        return {
            "search": self.search.text().strip(),
            "source": self.source_filter.currentText().strip(),
        }

    def _selected_history_items(self) -> list[dict]:
        return [self.history_rows[row] for row in self.list_widget.selected_rows() if 0 <= row < len(self.history_rows)]

    def _current_history(self) -> dict | None:
        selected = self._selected_history_items()
        return selected[0] if selected else None

    def _item_text(self, entry: dict) -> str:
        return " | ".join(
            [
                format_unix(entry.get("date_unix")),
                entry.get("voice_name", "Unknown voice"),
                f"model: {entry.get('model_id', 'n/a')}",
                f"source: {entry.get('source', 'n/a')}",
                f"state: {entry.get('state', 'n/a')}",
                (entry.get("text") or "")[:90],
            ]
        )

    def _update_selection_state(self) -> None:
        selected = self._selected_history_items()
        current = selected[0] if selected else None
        has_selection = bool(selected)
        self.play_button.setEnabled(bool(current))
        self.download_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
        self.selection_card.set_content(str(len(selected)), "Items currently selected")
        if not current:
            self.detail_label.setText("Select a history item to inspect it.")
            self.page_status.setText("Select one or more history entries to play, download, or delete.")
            return
        if len(selected) > 1:
            self.detail_label.setText(
                f"{len(selected)} history items selected. Play replays the first selection. "
                "Download and Delete apply to all selected items."
            )
            self.page_status.setText("Multiple history items selected.")
            return
        self.detail_label.setText(
            f"{format_unix(current.get('date_unix'))} | voice: {current.get('voice_name', 'Unknown')} | "
            f"model: {current.get('model_id', 'n/a')} | source: {current.get('source', 'n/a')} | "
            f"state: {current.get('state', 'n/a')}."
        )
        self.page_status.setText("Single history item selected.")

    def _emit_refresh(self) -> None:
        self.refresh_requested.emit(self.current_filters())

    def _emit_play(self) -> None:
        item = self._current_history()
        if item:
            self.play_requested.emit(item.get("history_item_id", ""))

    def _emit_download(self) -> None:
        selected = self._selected_history_items()
        if not selected:
            return
        ids = [item.get("history_item_id", "") for item in selected if item.get("history_item_id")]
        self.download_requested.emit(ids if len(ids) > 1 else ids[0])

    def _emit_delete(self) -> None:
        selected = self._selected_history_items()
        if not selected:
            return
        ids = [item.get("history_item_id", "") for item in selected if item.get("history_item_id")]
        self.delete_requested.emit(ids if len(ids) > 1 else ids[0])
