from __future__ import annotations

import contextlib
import io
from typing import Iterable

from PySide6.QtCore import QObject, QEvent, Qt, Signal
from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QTabWidget, QTextEdit, QWidget

try:  # pragma: no cover - optional dependency
    import accessible_output2.outputs.auto as accessible_output_auto
except Exception:  # pragma: no cover - optional dependency
    accessible_output_auto = None


class AccessibilityAnnouncer(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._speaker = None
        self.spoken_fallback_enabled = False
        if accessible_output_auto is not None:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try:
                    self._speaker = accessible_output_auto.Auto()
                except Exception:
                    self._speaker = None

    @property
    def has_spoken_output(self) -> bool:
        return self._speaker is not None

    def set_spoken_fallback_enabled(self, enabled: bool) -> None:
        self.spoken_fallback_enabled = bool(enabled)

    def announce(
        self,
        source: QWidget | None,
        message: str,
        *,
        assertive: bool = False,
        prefer_spoken_fallback: bool = True,
    ) -> None:
        text = message.strip()
        if not text:
            return

        widget = source or self.parent()
        if isinstance(widget, QWidget):
            try:
                event = QAccessibleAnnouncementEvent(widget, text)
                politeness = (
                    QAccessible.AnnouncementPoliteness.Assertive
                    if assertive
                    else QAccessible.AnnouncementPoliteness.Polite
                )
                event.setPoliteness(politeness)
                QAccessible.updateAccessibility(event)
            except Exception:
                pass

        if (
            prefer_spoken_fallback
            and self.spoken_fallback_enabled
            and self._speaker is not None
            and not QAccessible.isActive()
        ):
            try:
                self._speaker.speak(text, interrupt=assertive)
            except Exception:
                pass


class AccessibleTabWidget(QTabWidget):
    tab_announced = Signal(str)

    def __init__(self, name: str, description: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAccessibleName(name)
        self.setAccessibleDescription(description or name)
        self.setFocusPolicy(Qt.StrongFocus)
        self.tabBar().setFocusPolicy(Qt.StrongFocus)
        self.currentChanged.connect(self._emit_tab_announcement)

        self._next_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        self._next_shortcut.activated.connect(self.focus_next_tab)
        self._prev_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        self._prev_shortcut.activated.connect(self.focus_previous_tab)
        self._page_down_shortcut = QShortcut(QKeySequence("Ctrl+PgDown"), self)
        self._page_down_shortcut.activated.connect(self.focus_next_tab)
        self._page_up_shortcut = QShortcut(QKeySequence("Ctrl+PgUp"), self)
        self._page_up_shortcut.activated.connect(self.focus_previous_tab)

    def focus_next_tab(self) -> None:
        if self.count() <= 1:
            return
        self.setCurrentIndex((self.currentIndex() + 1) % self.count())
        self.tabBar().setFocus(Qt.ShortcutFocusReason)

    def focus_previous_tab(self) -> None:
        if self.count() <= 1:
            return
        self.setCurrentIndex((self.currentIndex() - 1) % self.count())
        self.tabBar().setFocus(Qt.ShortcutFocusReason)

    def _emit_tab_announcement(self) -> None:
        label = self.tabText(self.currentIndex()).replace("&", "").strip()
        if label:
            self.tab_announced.emit(label)


def set_tab_order_chain(*widgets: QWidget | None) -> None:
    filtered = [widget for widget in widgets if widget is not None]
    for first, second in zip(filtered, filtered[1:]):
        QWidget.setTabOrder(first, second)


class DeferredTabOrderChain(QObject):
    def __init__(self, host: QWidget, widgets: list[QWidget]) -> None:
        super().__init__(host)
        self.host = host
        self.widgets = widgets
        self.applied = False
        host.installEventFilter(self)
        self._try_apply()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.host and event.type() in {
            QEvent.Show,
            QEvent.ParentChange,
            QEvent.Polish,
            QEvent.WindowActivate,
        }:
            self._try_apply()
        return super().eventFilter(watched, event)

    def _try_apply(self) -> None:
        if self.applied:
            return
        if not self.widgets:
            self.applied = True
            return
        top_level = self.host.window()
        if top_level is None:
            return
        if any(widget is None or widget.window() is not top_level for widget in self.widgets):
            return
        set_tab_order_chain(*self.widgets)
        self.applied = True
        self.host.removeEventFilter(self)


def defer_tab_order_chain(host: QWidget, *widgets: QWidget | None) -> DeferredTabOrderChain:
    filtered = [widget for widget in widgets if widget is not None]
    chain = DeferredTabOrderChain(host, filtered)
    host._deferred_tab_order_chain = chain  # type: ignore[attr-defined]
    return chain


def configure_focusable_text_edit(editor: QTextEdit, *, name: str, description: str = "") -> None:
    editor.setTabChangesFocus(True)
    editor.setAccessibleName(name)
    if description:
        editor.setAccessibleDescription(description)
    editor.setFocusPolicy(Qt.StrongFocus)


def first_focusable_widget(widgets: Iterable[QWidget]) -> QWidget | None:
    for widget in widgets:
        if widget is not None and widget.focusPolicy() != Qt.NoFocus:
            return widget
    return None
