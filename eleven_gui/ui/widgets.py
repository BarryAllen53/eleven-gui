from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from eleven_gui.theme import COLORS


def fade_in(widget: QWidget, *, duration: int = 440, delay_ms: int = 0) -> None:
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setDuration(duration)
    animation.setEasingCurve(QEasingCurve.OutCubic)
    widget._fade_animation = animation  # type: ignore[attr-defined]
    QTimer.singleShot(delay_ms, animation.start)


def _pen(color: str, width: float = 1.8) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def build_icon(name: str, *, color: str | None = None, size: int = 24) -> QIcon:
    color = color or COLORS["text"]
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(_pen(color))
    painter.setBrush(Qt.NoBrush)

    s = size
    if name == "dashboard":
        for x in (4, s / 2 + 1):
            for y in (4, s / 2 + 1):
                painter.drawRoundedRect(int(x), int(y), s // 2 - 6, s // 2 - 6, 4, 4)
    elif name in {"voices", "library"}:
        painter.drawEllipse(4, 4, 8, 8)
        painter.drawLine(8, 12, 8, s - 4)
        painter.drawLine(8, s - 4, s - 6, s - 10)
        painter.drawPath(_sound_wave_path(s))
    elif name == "clone":
        painter.drawEllipse(2, 5, s - 11, s - 11)
        painter.drawEllipse(9, 8, s - 11, s - 11)
        painter.drawLine(9, s // 2, s - 8, s // 2)
    elif name == "studio":
        painter.drawPath(_sound_wave_path(s))
        painter.drawLine(4, s - 5, s - 4, s - 5)
    elif name == "history":
        painter.drawEllipse(4, 4, s - 8, s - 8)
        painter.drawLine(s // 2, s // 2, s // 2, 8)
        painter.drawLine(s // 2, s // 2, s - 7, s // 2 + 4)
    elif name == "settings":
        path = QPainterPath()
        path.addEllipse(s * 0.29, s * 0.29, s * 0.42, s * 0.42)
        painter.drawPath(path)
        for point in (
            QPoint(s // 2, 2),
            QPoint(s // 2, s - 2),
            QPoint(2, s // 2),
            QPoint(s - 2, s // 2),
        ):
            painter.drawLine(QPoint(s // 2, s // 2), point)
    elif name == "refresh":
        painter.drawArc(4, 4, s - 8, s - 8, 30 * 16, 270 * 16)
        painter.drawLine(s - 7, 7, s - 3, 3)
        painter.drawLine(s - 7, 7, s - 11, 4)
    elif name == "play":
        path = QPainterPath()
        path.moveTo(7, 5)
        path.lineTo(s - 6, s // 2)
        path.lineTo(7, s - 5)
        path.closeSubpath()
        painter.setBrush(QColor(color))
        painter.drawPath(path)
    elif name == "stop":
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(6, 6, s - 12, s - 12, 4, 4)
    elif name == "download":
        painter.drawLine(s // 2, 4, s // 2, s - 8)
        painter.drawLine(s // 2, s - 8, s // 2 - 5, s - 13)
        painter.drawLine(s // 2, s - 8, s // 2 + 5, s - 13)
        painter.drawLine(5, s - 4, s - 5, s - 4)
    elif name == "upload":
        painter.drawLine(s // 2, s - 4, s // 2, 8)
        painter.drawLine(s // 2, 8, s // 2 - 5, 13)
        painter.drawLine(s // 2, 8, s // 2 + 5, 13)
        painter.drawLine(5, s - 4, s - 5, s - 4)
    elif name == "save":
        painter.drawRoundedRect(5, 4, s - 10, s - 8, 3, 3)
        painter.drawLine(8, 8, s - 8, 8)
        painter.drawLine(8, s // 2, s - 8, s // 2)
    elif name == "delete":
        painter.drawLine(8, 8, s - 8, 8)
        painter.drawLine(10, 8, 9, s - 5)
        painter.drawLine(s - 10, 8, s - 9, s - 5)
        painter.drawLine(9, s - 5, s - 9, s - 5)
        painter.drawLine(11, 11, s - 11, s - 11)
        painter.drawLine(8, 5, s - 8, 5)
    elif name == "back":
        painter.drawLine(7, s // 2, s - 5, s // 2)
        painter.drawLine(7, s // 2, 12, s // 2 - 5)
        painter.drawLine(7, s // 2, 12, s // 2 + 5)
    elif name == "link":
        painter.drawRoundedRect(4, 9, s // 2 - 2, 6, 3, 3)
        painter.drawRoundedRect(s // 2 - 2, 9, s // 2 - 2, 6, 3, 3)
        painter.drawLine(s // 2 - 2, s // 2, s // 2 + 2, s // 2)
    else:
        painter.drawEllipse(4, 4, s - 8, s - 8)

    painter.end()
    return QIcon(pixmap)


def _sound_wave_path(size: int) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(4, size * 0.58)
    path.cubicTo(size * 0.18, size * 0.15, size * 0.26, size * 0.84, size * 0.42, size * 0.4)
    path.cubicTo(size * 0.54, size * 0.08, size * 0.6, size * 0.94, size * 0.76, size * 0.34)
    path.cubicTo(size * 0.83, size * 0.16, size * 0.9, size * 0.48, size - 4, size * 0.48)
    return path


class SidebarButton(QPushButton):
    def __init__(self, text: str, icon_name: str) -> None:
        super().__init__(text)
        self.setCheckable(True)
        self.setProperty("nav", "true")
        self.setCursor(Qt.PointingHandCursor)
        self.setIcon(build_icon(icon_name))
        self.setIconSize(QSize(22, 22))
        self.setAccessibleName(text)


class SectionCard(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("SectionCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFocusPolicy(Qt.NoFocus)
        fade_in(self, delay_ms=40)


class CollapsibleSection(SectionCard):
    def __init__(self, title: str, description: str = "", *, expanded: bool = False) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        self.toggle_button = QPushButton("")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(expanded)
        self.toggle_button.setProperty("variant", "subtle")
        self.toggle_button.clicked.connect(self._sync_state)
        self.toggle_button.setAccessibleName(title)

        self.description_label = QLabel(description)
        self.description_label.setProperty("role", "muted")
        self.description_label.setWordWrap(True)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)

        layout.addWidget(self.toggle_button)
        if description:
            layout.addWidget(self.description_label)
        layout.addWidget(self.content)
        self._title = title
        self._sync_state()

    def _sync_state(self) -> None:
        expanded = self.toggle_button.isChecked()
        action = "Hide" if expanded else "Show"
        self.toggle_button.setText(f"{action} {self._title}")
        self.content.setVisible(expanded)

    def set_expanded(self, expanded: bool) -> None:
        self.toggle_button.setChecked(expanded)
        self._sync_state()


class MetricCard(QFrame):
    def __init__(self, title: str, value: str = "N/A", caption: str = "") -> None:
        super().__init__()
        self.setObjectName("MetricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setProperty("role", "metric-title")
        self.value_label = QLabel(value)
        self.value_label.setProperty("role", "metric-value")
        self.caption_label = QLabel(caption)
        self.caption_label.setProperty("role", "muted")
        self.caption_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.caption_label)
        fade_in(self, delay_ms=80)

    def set_content(self, value: str, caption: str) -> None:
        self.value_label.setText(value)
        self.caption_label.setText(caption)


class HeroBanner(QFrame):
    def __init__(self, *, kicker: str, title: str, body: str, asset_path: Path) -> None:
        super().__init__()
        self.setObjectName("HeroBanner")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(26)

        left = QVBoxLayout()
        left.setSpacing(10)

        kicker_label = QLabel(kicker.upper())
        kicker_label.setProperty("role", "metric-title")
        self.title_label = QLabel(title)
        self.title_label.setProperty("role", "title")
        self.title_label.setWordWrap(True)
        self.body_label = QLabel(body)
        self.body_label.setProperty("role", "muted")
        self.body_label.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        self.primary_button = QPushButton("Refresh")
        self.primary_button.setProperty("variant", "primary")
        self.secondary_button = QPushButton("Open Settings")
        self.primary_button.setAccessibleName("Primary action")
        self.secondary_button.setAccessibleName("Secondary action")
        buttons.addWidget(self.primary_button)
        buttons.addWidget(self.secondary_button)
        buttons.addStretch(1)

        left.addWidget(kicker_label)
        left.addWidget(self.title_label)
        left.addWidget(self.body_label)
        left.addSpacing(10)
        left.addLayout(buttons)
        left.addStretch(1)

        art = QSvgWidget(str(asset_path))
        art.setMinimumSize(240, 180)
        art.setMaximumSize(360, 240)
        art.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addLayout(left, 4)
        layout.addWidget(art, 3)
        fade_in(self, delay_ms=20)


class LabeledSlider(QWidget):
    value_changed = Signal(float)

    def __init__(
        self,
        title: str,
        *,
        minimum: float,
        maximum: float,
        decimals: int = 2,
        initial: float | None = None,
    ) -> None:
        super().__init__()
        self.minimum = minimum
        self.maximum = maximum
        self.decimals = decimals
        self.scale = 10**decimals

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(title)
        self.title_label.setProperty("role", "metric-title")
        self.value_label = QLabel("")
        self.value_label.setProperty("role", "muted")
        row.addWidget(self.title_label)
        row.addStretch(1)
        row.addWidget(self.value_label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, int((self.maximum - self.minimum) * self.scale))
        self.slider.valueChanged.connect(self._emit_value)
        self.slider.setAccessibleName(title)

        layout.addLayout(row)
        layout.addWidget(self.slider)
        self.set_value(initial if initial is not None else self.minimum)

    def value(self) -> float:
        return self.minimum + (self.slider.value() / self.scale)

    def set_value(self, value: float) -> None:
        clamped = min(self.maximum, max(self.minimum, value))
        self.slider.blockSignals(True)
        self.slider.setValue(int(round((clamped - self.minimum) * self.scale)))
        self.slider.blockSignals(False)
        self.value_label.setText(f"{clamped:.{self.decimals}f}")

    def _emit_value(self) -> None:
        current = self.value()
        self.value_label.setText(f"{current:.{self.decimals}f}")
        self.value_changed.emit(current)


class VoiceSettingsEditor(QWidget):
    def __init__(self, title: str = "Voice Settings") -> None:
        super().__init__()
        self.setObjectName("VoiceSettingsEditor")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        heading = QLabel(title)
        heading.setProperty("role", "section-title")
        subtitle = QLabel("Use only when you want to shape stability, similarity, style or delivery speed.")
        subtitle.setProperty("role", "muted")
        subtitle.setWordWrap(True)

        self.stability = LabeledSlider("Stability", minimum=0.0, maximum=1.0, initial=0.5)
        self.similarity = LabeledSlider("Similarity", minimum=0.0, maximum=1.0, initial=0.75)
        self.style = LabeledSlider("Style", minimum=0.0, maximum=1.0, initial=0.0)
        self.speed = LabeledSlider("Speed", minimum=0.7, maximum=1.2, initial=1.0)
        self.speaker_boost = QCheckBox("Use speaker boost")
        self.speaker_boost.setChecked(True)
        self.speaker_boost.setAccessibleDescription("Preserves similarity to the original speaker when available.")

        layout.addWidget(heading)
        layout.addWidget(subtitle)
        layout.addWidget(self.stability)
        layout.addWidget(self.similarity)
        layout.addWidget(self.style)
        layout.addWidget(self.speed)
        layout.addWidget(self.speaker_boost)

    def settings(self) -> dict[str, float | bool]:
        return {
            "stability": round(self.stability.value(), 2),
            "similarity_boost": round(self.similarity.value(), 2),
            "style": round(self.style.value(), 2),
            "speed": round(self.speed.value(), 2),
            "use_speaker_boost": self.speaker_boost.isChecked(),
        }

    def set_settings(self, settings: dict[str, float | bool] | None) -> None:
        settings = settings or {}
        self.stability.set_value(float(settings.get("stability", 0.5)))
        self.similarity.set_value(float(settings.get("similarity_boost", 0.75)))
        self.style.set_value(float(settings.get("style", 0.0)))
        self.speed.set_value(float(settings.get("speed", 1.0)))
        self.speaker_boost.setChecked(bool(settings.get("use_speaker_boost", True)))


class DataTable(QTableWidget):
    def __init__(self, columns: list[str], *, accessible_name: str = "Data table") -> None:
        super().__init__(0, len(columns))
        self.setHorizontalHeaderLabels(columns)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setShowGrid(False)
        self.setTabKeyNavigation(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setHighlightSections(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setAccessibleName(accessible_name)
        self.setAccessibleDescription("Use arrow keys to move rows. Press Tab to leave the table.")
        self.viewport().setAccessibleName(accessible_name)
        self.viewport().setAccessibleDescription("Use arrow keys to browse rows.")

    def set_rows(self, rows: list[list[str]]) -> None:
        self.clearSelection()
        self.setRowCount(len(rows))
        for row_index, row_values in enumerate(rows):
            for column_index, value in enumerate(row_values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.setItem(row_index, column_index, item)
        if rows:
            self.setCurrentCell(0, 0)
            self.selectRow(0)


class AccessibleListWidget(QListWidget):
    files_dropped = Signal(object)
    order_changed = Signal(object)

    def __init__(
        self,
        accessible_name: str,
        *,
        multi_select: bool = False,
        drag_reorder: bool = False,
        accept_file_drop: bool = False,
    ) -> None:
        super().__init__()
        self._multi_select = multi_select
        self._drag_reorder = drag_reorder
        self._accept_file_drop = accept_file_drop
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection if multi_select else QAbstractItemView.SingleSelection)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setAutoScroll(True)
        self.setMouseTracking(True)
        self.setDragDropOverwriteMode(False)
        self.setAccessibleName(accessible_name)
        description = "Use Up, Down, Home and End to browse the list."
        if multi_select:
            description += " Use Shift or Control with the arrow keys to select multiple items."
        if drag_reorder:
            description += " Drag items to reorder them."
        if accept_file_drop:
            description += " Drop files here to add them."
        description += " Press Tab to leave the list."
        self.setAccessibleDescription(description)
        if drag_reorder:
            self.setDragEnabled(True)
            self.setAcceptDrops(True)
            self.viewport().setAcceptDrops(True)
            self.setDropIndicatorShown(True)
            self.setDragDropMode(QAbstractItemView.InternalMove)
            self.setDefaultDropAction(Qt.MoveAction)
        elif accept_file_drop:
            self.setAcceptDrops(True)
            self.viewport().setAcceptDrops(True)
            self.setDropIndicatorShown(True)

    def set_items(self, items: list[str], *, selected_rows: list[int] | None = None) -> None:
        self.clear()
        for text in items:
            item = QListWidgetItem(text)
            item.setToolTip(text)
            self.addItem(item)
        if not items:
            return
        if selected_rows:
            self.clearSelection()
            first_row = -1
            for row in selected_rows:
                item = self.item(row)
                if item is None:
                    continue
                item.setSelected(True)
                if first_row < 0:
                    first_row = row
            if first_row >= 0:
                self.setCurrentRow(first_row)
                return
        self.setCurrentRow(0)

    def selectRow(self, row: int) -> None:
        self.setCurrentRow(row)

    def selected_rows(self) -> list[int]:
        rows = sorted({self.row(item) for item in self.selectedItems() if self.row(item) >= 0})
        if rows:
            return rows
        current = self.currentRow()
        return [current] if current >= 0 else []

    def primary_selected_row(self) -> int:
        rows = self.selected_rows()
        return rows[0] if rows else -1

    def ordered_item_data(self, role: int = Qt.UserRole) -> list[object]:
        values: list[object] = []
        for row in range(self.count()):
            item = self.item(row)
            values.append(item.data(role) if item is not None else None)
        return values

    def dragEnterEvent(self, event) -> None:  # pragma: no cover - GUI path
        if self._accept_file_drop and event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # pragma: no cover - GUI path
        if self._accept_file_drop and event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # pragma: no cover - GUI path
        if self._accept_file_drop and event.mimeData().hasUrls():
            files = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            files = [path for path in files if path]
            if files:
                self.files_dropped.emit(files)
                event.acceptProposedAction()
                return
        super().dropEvent(event)
        if self._drag_reorder:
            self.order_changed.emit(self.ordered_item_data())


class PlayerDock(QFrame):
    play_requested = Signal()
    stop_requested = Signal()
    folder_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PlayerDock")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        self.play_button = QPushButton("Play")
        self.play_button.setIcon(build_icon("play"))
        self.play_button.setProperty("variant", "primary")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setIcon(build_icon("stop"))
        self.open_button = QPushButton("Open Folder")
        self.open_button.setIcon(build_icon("download"))
        self.title_label = QLabel("No audio selected")
        self.title_label.setProperty("role", "section-title")
        self.meta_label = QLabel("Preview URLs ve uretilen ciktilar burada oynatilir.")
        self.meta_label.setProperty("role", "muted")

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        text_box.addWidget(self.title_label)
        text_box.addWidget(self.meta_label)

        layout.addWidget(self.play_button)
        layout.addWidget(self.stop_button)
        layout.addLayout(text_box, 1)
        layout.addWidget(self.open_button)
        self.open_button.setEnabled(False)

        self.play_button.clicked.connect(self.play_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.open_button.clicked.connect(self.folder_requested.emit)
        self.play_button.setAccessibleName("Play current audio")
        self.stop_button.setAccessibleName("Stop current audio")
        self.open_button.setAccessibleName("Open current audio folder")

    def set_track(self, title: str, meta: str) -> None:
        self.title_label.setText(title)
        self.meta_label.setText(meta)


class AudioResultCard(SectionCard):
    replay_requested = Signal()
    stop_requested = Signal()
    regenerate_requested = Signal()
    download_requested = Signal()

    def __init__(self, title: str = "Generated Audio") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        self.heading = QLabel(title)
        self.heading.setProperty("role", "section-title")
        self.title_label = QLabel("No generated audio yet.")
        self.title_label.setWordWrap(True)
        self.meta_label = QLabel("Play and stop controls appear only after a result is ready.")
        self.meta_label.setProperty("role", "muted")
        self.meta_label.setWordWrap(True)

        buttons = QHBoxLayout()
        self.replay_button = QPushButton("&Replay")
        self.replay_button.setIcon(build_icon("play"))
        self.replay_button.setProperty("variant", "primary")
        self.stop_button = QPushButton("S&top")
        self.stop_button.setIcon(build_icon("stop"))
        self.regenerate_button = QPushButton("&Regenerate")
        self.regenerate_button.setIcon(build_icon("refresh"))
        self.download_button = QPushButton("&Download")
        self.download_button.setIcon(build_icon("download"))
        buttons.addWidget(self.replay_button)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.regenerate_button)
        buttons.addWidget(self.download_button)
        buttons.addStretch(1)

        self.replay_button.clicked.connect(self.replay_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.regenerate_button.clicked.connect(self.regenerate_requested.emit)
        self.download_button.clicked.connect(self.download_requested.emit)
        self.replay_button.setAccessibleName("Replay generated audio")
        self.stop_button.setAccessibleName("Stop generated audio")
        self.regenerate_button.setAccessibleName("Generate the last request again")
        self.download_button.setAccessibleName("Download generated audio")

        layout.addWidget(self.heading)
        layout.addWidget(self.title_label)
        layout.addWidget(self.meta_label)
        layout.addLayout(buttons)
        self.clear()

    def clear(self) -> None:
        self.setVisible(False)
        self.title_label.setText("No generated audio yet.")
        self.meta_label.setText("Replay, regenerate and download appear only after a result is ready.")
        self.download_button.setEnabled(False)
        self.regenerate_button.setEnabled(False)

    def set_result(self, title: str, meta: str, *, can_open_folder: bool = True) -> None:
        self.setVisible(True)
        self.title_label.setText(title)
        self.meta_label.setText(meta)
        self.download_button.setEnabled(can_open_folder)
        self.regenerate_button.setEnabled(True)


class ProgressStatusCard(SectionCard):
    cancel_requested = Signal()

    def __init__(self, title: str = "Operation Status") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        self.heading = QLabel(title)
        self.heading.setProperty("role", "section-title")
        self.status_label = QLabel("Idle.")
        self.status_label.setWordWrap(True)
        self.percent_label = QLabel("0%")
        self.percent_label.setProperty("role", "muted")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setAccessibleName("Operation progress")
        self.detail_label = QLabel("No active operation.")
        self.detail_label.setProperty("role", "muted")
        self.detail_label.setWordWrap(True)
        self.cancel_button = QPushButton("&Cancel")
        self.cancel_button.setProperty("variant", "danger")
        self.cancel_button.clicked.connect(self.cancel_requested.emit)

        layout.addWidget(self.heading)
        layout.addWidget(self.status_label)
        layout.addWidget(self.percent_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.detail_label)
        layout.addWidget(self.cancel_button)
        self.set_state(0, "Idle.", "No active operation.", running=False)

    def set_state(self, percent: int, status: str, detail: str, *, running: bool) -> None:
        self.progress_bar.setValue(max(0, min(100, percent)))
        self.status_label.setText(status)
        self.percent_label.setText(f"{max(0, min(100, percent))}%")
        self.detail_label.setText(detail)
        self.cancel_button.setVisible(running)
