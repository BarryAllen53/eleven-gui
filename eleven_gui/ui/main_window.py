from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThreadPool, QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from eleven_gui.accessibility import AccessibilityAnnouncer
from eleven_gui.api.client import ApiError, AudioPayload, BinaryPayload, ElevenLabsClient
from eleven_gui.config import AppConfig, save_api_key
from eleven_gui.services.workers import Worker
from eleven_gui.ui.pages.clone_lab_page import CloneLabPage
from eleven_gui.ui.pages.dashboard_page import DashboardPage
from eleven_gui.ui.pages.history_page import HistoryPage
from eleven_gui.ui.pages.settings_page import SettingsPage
from eleven_gui.ui.pages.studio_page import StudioPage
from eleven_gui.ui.pages.voice_hub_page import VoiceHubPage
from eleven_gui.ui.widgets import SidebarButton, build_icon
from eleven_gui.utils import content_type_to_suffix, parse_labels, timestamped_file


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.client = ElevenLabsClient(config.api_key) if config.api_key else None
        self.announcer = AccessibilityAnnouncer(self)
        self.announcer.set_spoken_fallback_enabled(False)
        self.thread_pool = QThreadPool.globalInstance()
        self.pending_tasks = 0
        self.current_audio_target = ""
        self.current_audio_is_local = False
        self.last_generation_request: dict[str, object] | None = None
        self.current_page_key = "dashboard"
        self.navigation_history: list[str] = []
        self.clone_worker: Worker | None = None
        self.last_clone_progress_percent = -1
        self._registered_shortcuts: list[QShortcut] = []
        self._active_workers: list[Worker] = []
        self._pending_missing_voice_count = 0
        self._missing_voice_notice_timer = QTimer(self)
        self._missing_voice_notice_timer.setSingleShot(True)
        self._missing_voice_notice_timer.timeout.connect(self._flush_missing_voice_notice)
        self.state: dict[str, object] = {
            "subscription": {},
            "user": {},
            "models": [],
            "voices": [],
            "history": [],
            "shared": {},
            "selected_voice": None,
        }

        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.85)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)

        self.setWindowTitle("Eleven GUI")
        self.setAccessibleName("Eleven GUI main window")
        self.setAccessibleDescription("Desktop client for ElevenLabs with accessible keyboard navigation.")
        self.resize(1520, 980)
        self._build_ui()
        self._bind_page_signals()
        self._apply_api_state("Ready.")

        if self.client:
            self.refresh_all()
        else:
            self.switch_page("settings", push_history=False)
            self._apply_api_state("API key not loaded. Open Settings.")

    def closeEvent(self, event) -> None:  # pragma: no cover - GUI close path
        self.player.stop()
        if self.clone_worker:
            self.clone_worker.cancel()
        self.thread_pool.waitForDone(3000)
        if self.client:
            self.client.close()
        super().closeEvent(event)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setAccessibleName("Application root")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(20)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(252)
        sidebar.setAccessibleName("Main navigation")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 22, 20, 22)
        sidebar_layout.setSpacing(16)

        brand = QLabel("ELEVEN\nVOICE")
        brand.setProperty("role", "title")
        brand_sub = QLabel("Minimal desktop workspace\nfor ElevenLabs operations")
        brand_sub.setProperty("role", "muted")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(brand_sub)

        self.nav_buttons: dict[str, SidebarButton] = {}
        for key, label, icon in (
            ("dashboard", "Overview", "dashboard"),
            ("voices", "Voice Hub", "voices"),
            ("clone", "Clone Lab", "clone"),
            ("studio", "Studio", "studio"),
            ("history", "History", "history"),
            ("settings", "Settings", "settings"),
        ):
            button = SidebarButton(label, icon)
            button.clicked.connect(lambda checked=False, page_key=key: self.switch_page(page_key))
            sidebar_layout.addWidget(button)
            self.nav_buttons[key] = button

        sidebar_layout.addStretch(1)
        self.sidebar_source = QLabel(f"Key source: {self.config.api_key_source}")
        self.sidebar_source.setProperty("role", "muted")
        sidebar_layout.addWidget(self.sidebar_source)

        content = QWidget()
        content.setAccessibleName("Main content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(18)

        top_shell = QFrame()
        top_shell.setObjectName("TopShell")
        top_layout = QHBoxLayout(top_shell)
        top_layout.setContentsMargins(22, 18, 22, 18)
        top_layout.setSpacing(18)
        self.back_button = QPushButton("&Back")
        self.back_button.setIcon(build_icon("back"))
        self.back_button.setAccessibleDescription("Return to the previous page.")
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setEnabled(False)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.page_title = QLabel("Overview")
        self.page_title.setProperty("role", "title")
        self.page_subtitle = QLabel("Workspace snapshot")
        self.page_subtitle.setProperty("role", "muted")
        self.page_title.setAccessibleName("Current page title")
        self.page_subtitle.setAccessibleName("Current page subtitle")
        title_box.addWidget(self.page_title)
        title_box.addWidget(self.page_subtitle)

        self.status_label = QLabel("Ready.")
        self.status_label.setProperty("role", "muted")
        self.status_label.setAccessibleName("Application status")
        self.refresh_button = QPushButton("&Refresh Workspace")
        self.refresh_button.setIcon(build_icon("refresh"))
        self.refresh_button.setProperty("variant", "primary")
        self.refresh_button.setAccessibleDescription("Reloads subscription, models, voices, shared library, and history.")
        self.refresh_button.clicked.connect(self.refresh_all)
        top_layout.addWidget(self.back_button)
        top_layout.addLayout(title_box, 1)
        top_layout.addWidget(self.status_label)
        top_layout.addWidget(self.refresh_button)

        self.stack = QStackedWidget()
        self.dashboard_page = DashboardPage(self.config.assets_dir)
        self.voice_page = VoiceHubPage()
        self.clone_page = CloneLabPage(self.config.assets_dir)
        self.studio_page = StudioPage()
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage()

        self.page_meta = {
            "dashboard": ("Overview", "Workspace pulse and credit visibility"),
            "voices": ("Voice Hub", "Manage voices and route them into Studio"),
            "clone": ("Clone Lab", "Create instant or professional voice clones"),
            "studio": ("Studio", "Use a selected voice for TTS or STS"),
            "history": ("History", "Browse, replay, and download generations"),
            "settings": ("Settings", "API key, docs, and accessibility behavior"),
        }
        self.page_order = ["dashboard", "voices", "clone", "studio", "history", "settings"]
        self.page_widgets = {
            "dashboard": self.dashboard_page,
            "voices": self.voice_page,
            "clone": self.clone_page,
            "studio": self.studio_page,
            "history": self.history_page,
            "settings": self.settings_page,
        }
        for page in (
            self.dashboard_page,
            self.voice_page,
            self.clone_page,
            self.studio_page,
            self.history_page,
            self.settings_page,
        ):
            self.stack.addWidget(self._wrap_page(page))

        content_layout.addWidget(top_shell)
        content_layout.addWidget(self.stack, 1)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)
        self._register_shortcuts()
        self._configure_global_tab_order()
        self.switch_page("dashboard", push_history=False)

        self.settings_page.set_api_state(
            key_value=self.config.api_key,
            source=self.config.api_key_source,
            status="Ready to test current key." if self.config.api_key else "No key loaded yet.",
            spoken_fallback=False,
        )

    def _wrap_page(self, page: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setFocusPolicy(Qt.NoFocus)
        scroll.viewport().setFocusPolicy(Qt.NoFocus)
        scroll.setAccessibleName(f"{page.accessibleName() or 'Page'} container")
        scroll.setWidget(page)
        return scroll

    def _register_shortcuts(self) -> None:
        for index, page_key in enumerate(self.page_order, start=1):
            self._add_shortcut(f"Ctrl+{index}", lambda key=page_key: self.switch_page(key))
        self._add_shortcut("F6", lambda: self._cycle_focus_region(1))
        self._add_shortcut("Shift+F6", lambda: self._cycle_focus_region(-1))
        self._add_shortcut("Alt+Left", self.go_back)
        self._add_shortcut("F5", self.refresh_all)
        self._add_shortcut("F1", self.show_shortcuts_help)
        self._add_shortcut("Ctrl+/", self.show_shortcuts_help)
        self._add_shortcut("Ctrl+L", self.focus_primary_input)
        self._add_shortcut("Ctrl+E", self.focus_studio_editor)
        self._add_shortcut("Ctrl+S", self.trigger_settings_save)
        self._add_shortcut("Ctrl+T", self.trigger_settings_test)
        self._add_shortcut("Ctrl+Shift+R", self.trigger_context_refresh)
        self._add_shortcut("Ctrl+Shift+P", self.trigger_context_preview_or_play)
        self._add_shortcut("Ctrl+Shift+U", self.trigger_context_use_action)
        self._add_shortcut("Ctrl+Shift+S", self.trigger_context_save_or_stop)
        self._add_shortcut("Ctrl+Shift+D", self.trigger_context_download)
        self._add_shortcut("Ctrl+Shift+G", self.trigger_context_regenerate)
        self._add_shortcut("Ctrl+Shift+A", self.trigger_context_add_samples)
        self._add_shortcut("Ctrl+Shift+C", self.trigger_context_create_clone)
        self._add_shortcut("Ctrl+Shift+Q", self.trigger_context_fetch_captcha)
        self._add_shortcut("Ctrl+Shift+V", self.trigger_context_verify_owner)
        self._add_shortcut("Ctrl+Shift+T", self.trigger_context_train_or_test)
        self._add_shortcut("Ctrl+Shift+X", self.trigger_context_cancel_or_stop)
        self._add_shortcut("Ctrl+Enter", self.trigger_context_primary_action)
        self._add_shortcut("Ctrl+O", self.trigger_context_open_file)
        self._add_shortcut("Delete", self.trigger_context_delete)
        self._add_shortcut("Ctrl+Alt+1", lambda: self.trigger_context_switch_tab(0))
        self._add_shortcut("Ctrl+Alt+2", lambda: self.trigger_context_switch_tab(1))
        self._add_shortcut("Ctrl+Alt+3", lambda: self.trigger_context_switch_tab(2))

    def _add_shortcut(self, sequence: str, handler) -> None:
        shortcut = QShortcut(QKeySequence(sequence), self)
        shortcut.setContext(Qt.ApplicationShortcut)
        shortcut.activated.connect(handler)
        self._registered_shortcuts.append(shortcut)

    def _configure_global_tab_order(self) -> None:
        nav_chain = [
            self.nav_buttons["dashboard"],
            self.nav_buttons["voices"],
            self.nav_buttons["clone"],
            self.nav_buttons["studio"],
            self.nav_buttons["history"],
            self.nav_buttons["settings"],
            self.back_button,
            self.refresh_button,
        ]
        for first, second in zip(nav_chain, nav_chain[1:]):
            QWidget.setTabOrder(first, second)

    def _bind_page_signals(self) -> None:
        self.dashboard_page.refresh_requested.connect(self.refresh_all)
        self.dashboard_page.settings_requested.connect(lambda: self.switch_page("settings"))
        self.voice_page.tabs.tab_announced.connect(lambda label: self._announce_ui(f"Voice Hub tab: {label}."))
        self.voice_page.refresh_voices_requested.connect(self.refresh_voices)
        self.voice_page.refresh_shared_requested.connect(self.refresh_shared_voices)
        self.voice_page.voice_selected.connect(self.load_voice_details)
        self.voice_page.preview_requested.connect(self.play_remote_preview)
        self.voice_page.save_metadata_requested.connect(self.save_voice_metadata)
        self.voice_page.delete_voice_requested.connect(self.delete_voice)
        self.voice_page.add_shared_requested.connect(self.add_shared_voice)
        self.voice_page.use_voice_requested.connect(self.use_voice_in_studio)

        self.clone_page.create_clone_requested.connect(self.create_clone)
        self.clone_page.preview_sample_requested.connect(self.play_local_sample_preview)
        self.clone_page.stop_preview_requested.connect(self.player.stop)
        self.clone_page.preview_clone_requested.connect(self.play_remote_preview)
        self.clone_page.use_clone_requested.connect(self.use_voice_in_studio)
        self.clone_page.delete_clone_requested.connect(self.delete_voice)
        self.clone_page.fetch_pvc_captcha_requested.connect(self.fetch_pvc_captcha)
        self.clone_page.verify_pvc_captcha_requested.connect(self.verify_pvc_captcha)
        self.clone_page.train_pvc_requested.connect(self.train_pvc_voice)
        self.clone_page.cancel_clone_requested.connect(self.cancel_clone_task)

        self.studio_page.tabs.tab_announced.connect(lambda label: self._announce_ui(f"Studio tab: {label}."))
        self.studio_page.tts_requested.connect(self.generate_tts)
        self.studio_page.sts_requested.connect(self.generate_sts)
        self.studio_page.replay_result_requested.connect(self.replay_current_audio)
        self.studio_page.stop_result_requested.connect(self.player.stop)
        self.studio_page.regenerate_result_requested.connect(self.regenerate_last_audio)
        self.studio_page.download_result_requested.connect(self.download_current_audio)

        self.history_page.refresh_requested.connect(self.refresh_history)
        self.history_page.play_requested.connect(self.play_history_audio)
        self.history_page.download_requested.connect(self.download_history_audio)
        self.history_page.delete_requested.connect(self.delete_history_item)

        self.settings_page.save_requested.connect(self.store_api_key)
        self.settings_page.test_requested.connect(self.test_api_key)
        self.settings_page.spoken_fallback_toggled.connect(self._set_spoken_fallback)

    def switch_page(self, key: str, *, push_history: bool = True) -> None:
        if key not in self.page_order:
            return
        if push_history and key != self.current_page_key:
            self.navigation_history.append(self.current_page_key)
        self.current_page_key = key
        self.back_button.setEnabled(bool(self.navigation_history))
        for page_key, button in self.nav_buttons.items():
            button.setChecked(page_key == key)
        self.stack.setCurrentIndex(self.page_order.index(key))
        title, subtitle = self.page_meta[key]
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)
        focus_target = self._current_page_focus_target()
        if focus_target is not None:
            QTimer.singleShot(0, lambda target=focus_target: target.setFocus(Qt.TabFocusReason))
        self._announce_ui(f"{title}. {subtitle}")

    def go_back(self) -> None:
        if not self.navigation_history:
            return
        previous = self.navigation_history.pop()
        self.switch_page(previous, push_history=False)

    def _current_page_focus_target(self) -> QWidget | None:
        page = self.page_widgets.get(self.page_order[self.stack.currentIndex()])
        if page is None:
            return None
        target = getattr(page, "initial_focus_widget", None)
        if isinstance(target, QWidget):
            return target
        if isinstance(page, QWidget):
            return page
        return None

    def _focus_regions(self) -> list[QWidget]:
        page_target = self._current_page_focus_target() or self.refresh_button
        return [self.nav_buttons["dashboard"], self.back_button, page_target]

    def _cycle_focus_region(self, step: int) -> None:
        regions = self._focus_regions()
        if not regions:
            return
        current = QApplication.focusWidget()
        try:
            current_index = next(index for index, widget in enumerate(regions) if widget is current or widget.isAncestorOf(current))
        except StopIteration:
            current_index = -1
        next_widget = regions[(current_index + step) % len(regions)]
        next_widget.setFocus(Qt.ShortcutFocusReason)
        widget_label = next_widget.accessibleName()
        if not widget_label and hasattr(next_widget, "text"):
            widget_label = next_widget.text()
        self._announce_ui(f"Focus moved to {widget_label or 'section'}.")

    def _require_client(self) -> ElevenLabsClient | None:
        if not self.client:
            QMessageBox.warning(self, "Missing API key", "Configure your ElevenLabs API key first.")
            self.switch_page("settings")
            return None
        return self.client

    def _start_task(self, label: str, fn, on_success) -> None:
        worker = Worker(fn)
        self._active_workers.append(worker)
        self.pending_tasks += 1
        self._apply_api_state(label)
        worker.signals.success.connect(on_success)
        worker.signals.error.connect(lambda message: self._handle_task_error(label, message))
        worker.signals.finished.connect(lambda current=worker: self._finish_task(current))
        self.thread_pool.start(worker)

    def _finish_task(self, worker: Worker | None = None) -> None:
        if worker is not None and worker in self._active_workers:
            self._active_workers.remove(worker)
        self.pending_tasks = max(0, self.pending_tasks - 1)
        if self.pending_tasks == 0:
            self._apply_api_state("Ready.")

    def _handle_task_error(self, label: str, message: str) -> None:
        self._apply_api_state(f"{label} failed.")
        self._announce_ui(f"{label} failed.", assertive=True)
        summary = message.splitlines()[0]
        self.voice_page.show_voice_feedback(summary)
        self.clone_page.show_status(summary)
        self.studio_page.show_status(summary)
        QMessageBox.critical(self, "Request failed", summary)

    def _apply_api_state(self, text: str) -> None:
        self.status_label.setText(text)

    def _announce_ui(self, message: str, *, assertive: bool = False) -> None:
        self.announcer.announce(self, message, assertive=assertive)

    def _normalize_ids(self, selection: object) -> list[str]:
        if isinstance(selection, str):
            return [selection] if selection else []
        if isinstance(selection, (list, tuple, set)):
            values: list[str] = []
            for item in selection:
                if isinstance(item, str) and item and item not in values:
                    values.append(item)
            return values
        return []

    def _is_missing_voice_error(self, error: ApiError) -> bool:
        payload = error.details
        if isinstance(payload, dict) and isinstance(payload.get("detail"), dict):
            payload = payload.get("detail")
        if not isinstance(payload, dict):
            return False
        markers = {
            str(payload.get("type", "")).casefold(),
            str(payload.get("code", "")).casefold(),
            str(payload.get("status", "")).casefold(),
        }
        return any(
            marker in {"not_found", "voice_not_found", "voice_does_not_exist"}
            for marker in markers
            if marker
        )

    def _apply_voice_inventory(self, voices: list[dict]) -> None:
        self.state["voices"] = voices
        selected_voice = self.state.get("selected_voice")
        if isinstance(selected_voice, dict):
            selected_id = selected_voice.get("voice_id", "")
            if selected_id and not any(voice.get("voice_id", "") == selected_id for voice in voices):
                self.state["selected_voice"] = None
        self.voice_page.set_voices(voices)
        self.clone_page.set_cloned_voices(voices)
        self.studio_page.set_voice_options(voices)

    def _prune_missing_voice_ids(self, voice_ids: list[str]) -> int:
        unique_ids = [voice_id for voice_id in self._normalize_ids(voice_ids) if voice_id]
        if not unique_ids:
            return 0
        voices = list(self.state.get("voices", []))
        filtered = [voice for voice in voices if voice.get("voice_id", "") not in unique_ids]
        removed_count = len(voices) - len(filtered)
        if removed_count <= 0:
            return 0
        self._apply_voice_inventory(filtered)
        return removed_count

    def _queue_missing_voice_notice(self, removed_count: int) -> None:
        if removed_count <= 0:
            return
        self._pending_missing_voice_count += removed_count
        self._missing_voice_notice_timer.start(180)

    def _flush_missing_voice_notice(self) -> None:
        removed_count = self._pending_missing_voice_count
        self._pending_missing_voice_count = 0
        if removed_count <= 0:
            return
        message = (
            "Removed 1 unavailable voice from the list."
            if removed_count == 1
            else f"Removed {removed_count} unavailable voices from the list."
        )
        self.voice_page.show_voice_feedback(message)
        self.clone_page.show_status(message)
        self.studio_page.show_status(message)
        self._apply_api_state(message)
        self._announce_ui(message)

    def _set_spoken_fallback(self, enabled: bool) -> None:
        self.announcer.set_spoken_fallback_enabled(enabled)
        status = "Spoken fallback enabled." if enabled else "Spoken fallback disabled."
        self.settings_page.status_label.setText(status)
        self._apply_api_state(status)

    def show_shortcuts_help(self) -> None:
        sections = [
            "Global",
            "Ctrl+1..6: Switch main pages",
            "Alt+Left: Back",
            "F5: Refresh workspace",
            "F6 / Shift+F6: Move focus between major regions",
            "Ctrl+L: Focus the primary field for the current page",
            "Ctrl+Tab / Ctrl+Shift+Tab: Switch inner tabs",
            "F1 or Ctrl+/: Open shortcut help",
            "",
            "Voice Hub",
            "Ctrl+Alt+1: My Voices tab",
            "Ctrl+Alt+2: Cloned Voices tab",
            "Ctrl+Alt+3: Voice Library tab",
            "Ctrl+Shift+R: Refresh current voice section",
            "Ctrl+Shift+P: Preview selected voice",
            "Ctrl+Shift+U: Use the first selected voice in Studio",
            "Ctrl+Shift+S: Save metadata, or add all selected shared voices",
            "Delete: Delete all selected voices or clones",
            "",
            "Studio",
            "Ctrl+Alt+1: Text to Speech tab",
            "Ctrl+Alt+2: Speech to Speech tab",
            "Ctrl+E: Focus TTS text",
            "Ctrl+Enter: Generate for the current Studio tab",
            "Ctrl+Shift+P: Replay result",
            "Ctrl+Shift+G: Regenerate",
            "Ctrl+Shift+D: Download generated audio",
            "Ctrl+Shift+X: Stop playback",
            "Ctrl+O: Browse source audio in STS",
            "",
            "Clone Lab",
            "Ctrl+Shift+A: Add samples",
            "Ctrl+Shift+C: Create clone",
            "Ctrl+Shift+P: Preview the first selected sample or clone",
            "Ctrl+Shift+U: Use the first selected clone in Studio",
            "Ctrl+Shift+Q: Fetch PVC captcha",
            "Ctrl+Shift+V: Verify PVC owner",
            "Ctrl+Shift+T: Start PVC training",
            "Ctrl+Shift+X: Cancel clone task or stop preview",
            "Delete: Delete all selected clones",
            "",
            "History",
            "Ctrl+Shift+R: Refresh history",
            "Ctrl+Shift+P: Play the first selected history item",
            "Ctrl+Shift+D: Download all selected history items",
            "Delete: Delete all selected history items",
            "",
            "Settings",
            "Ctrl+S: Save API key",
            "Ctrl+T: Test API key",
        ]
        text = "\n".join(sections)
        QMessageBox.information(self, "Keyboard Shortcuts", text)
        self._announce_ui("Keyboard shortcuts help opened.")

    def focus_primary_input(self) -> None:
        if self.current_page_key == "voices":
            index = self.voice_page.tabs.currentIndex()
            target = (
                self.voice_page.my_search
                if index == 0
                else self.voice_page.cloned_search
                if index == 1
                else self.voice_page.library_search
            )
            target.setFocus(Qt.ShortcutFocusReason)
            return
        if self.current_page_key == "studio":
            if self.studio_page.tabs.currentIndex() == 0:
                self.studio_page.tts_text.setFocus(Qt.ShortcutFocusReason)
            else:
                self.studio_page.sts_file.setFocus(Qt.ShortcutFocusReason)
            return
        if self.current_page_key == "clone":
            self.clone_page.clone_name.setFocus(Qt.ShortcutFocusReason)
            return
        if self.current_page_key == "history":
            self.history_page.search.setFocus(Qt.ShortcutFocusReason)
            return
        if self.current_page_key == "settings":
            self.settings_page.key_input.setFocus(Qt.ShortcutFocusReason)

    def focus_studio_editor(self) -> None:
        if self.current_page_key == "studio" and self.studio_page.tabs.currentIndex() == 0:
            self.studio_page.tts_text.setFocus(Qt.ShortcutFocusReason)

    def trigger_settings_save(self) -> None:
        if self.current_page_key == "settings":
            self.settings_page.save_button.click()

    def trigger_settings_test(self) -> None:
        if self.current_page_key == "settings":
            self.settings_page.test_button.click()

    def trigger_context_refresh(self) -> None:
        if self.current_page_key == "voices":
            index = self.voice_page.tabs.currentIndex()
            if index == 2:
                self.voice_page.library_refresh_button.click()
            elif index == 1:
                self.voice_page.cloned_refresh_button.click()
            else:
                self.voice_page.my_refresh_button.click()
            return
        if self.current_page_key == "history":
            self.history_page.refresh_button.click()
            return
        self.refresh_all()

    def trigger_context_preview_or_play(self) -> None:
        if self.current_page_key == "voices":
            index = self.voice_page.tabs.currentIndex()
            if index == 2:
                self.voice_page.library_preview_button.click()
            elif index == 1:
                self.voice_page.cloned_preview_button.click()
            else:
                self.voice_page.my_preview_button.click()
            return
        if self.current_page_key == "studio":
            if self.studio_page.result_card.isVisible():
                self.studio_page.result_card.replay_button.click()
            return
        if self.current_page_key == "clone":
            if self.clone_page.clone_table.hasFocus():
                self.clone_page.preview_clone_button.click()
            else:
                self.clone_page.preview_sample_button.click()
            return
        if self.current_page_key == "history":
            self.history_page.play_button.click()

    def trigger_context_use_action(self) -> None:
        if self.current_page_key == "voices":
            index = self.voice_page.tabs.currentIndex()
            if index == 1:
                self.voice_page.cloned_use_voice_button.click()
            elif index == 0:
                self.voice_page.my_use_voice_button.click()
            return
        if self.current_page_key == "clone":
            self.clone_page.use_clone_button.click()

    def trigger_context_save_or_stop(self) -> None:
        if self.current_page_key == "voices":
            index = self.voice_page.tabs.currentIndex()
            if index == 2:
                self.voice_page.add_shared_button.click()
            elif index == 1:
                self.voice_page.cloned_save_meta_button.click()
            else:
                self.voice_page.my_save_meta_button.click()
            return
        if self.current_page_key == "studio" and self.studio_page.result_card.isVisible():
            self.studio_page.result_card.stop_button.click()
            return
        if self.current_page_key == "settings":
            self.settings_page.save_button.click()

    def trigger_context_download(self) -> None:
        if self.current_page_key == "studio" and self.studio_page.result_card.isVisible():
            self.studio_page.result_card.download_button.click()
            return
        if self.current_page_key == "history":
            self.history_page.download_button.click()

    def trigger_context_regenerate(self) -> None:
        if self.current_page_key == "studio" and self.studio_page.result_card.isVisible():
            self.studio_page.result_card.regenerate_button.click()

    def trigger_context_add_samples(self) -> None:
        if self.current_page_key == "clone":
            self.clone_page.pick_button.click()

    def trigger_context_create_clone(self) -> None:
        if self.current_page_key == "clone":
            self.clone_page.create_button.click()

    def trigger_context_fetch_captcha(self) -> None:
        if self.current_page_key == "clone":
            self.clone_page.fetch_captcha_button.click()

    def trigger_context_verify_owner(self) -> None:
        if self.current_page_key == "clone":
            self.clone_page.verify_captcha_button.click()

    def trigger_context_train_or_test(self) -> None:
        if self.current_page_key == "clone":
            self.clone_page.train_button.click()
            return
        if self.current_page_key == "settings":
            self.settings_page.test_button.click()

    def trigger_context_cancel_or_stop(self) -> None:
        if self.current_page_key == "clone":
            if self.clone_worker:
                self.clone_page.progress_card.cancel_button.click()
            else:
                self.clone_page.stop_sample_button.click()
            return
        if self.current_page_key == "studio" and self.studio_page.result_card.isVisible():
            self.studio_page.result_card.stop_button.click()

    def trigger_context_primary_action(self) -> None:
        if self.current_page_key == "studio":
            if self.studio_page.tabs.currentIndex() == 0:
                self.studio_page.tts_button.click()
            else:
                self.studio_page.sts_button.click()
            return
        if self.current_page_key == "voices":
            self.trigger_context_use_action()
            return
        if self.current_page_key == "clone":
            self.clone_page.create_button.click()

    def trigger_context_open_file(self) -> None:
        if self.current_page_key == "studio" and self.studio_page.tabs.currentIndex() == 1:
            self.studio_page.pick_button.click()
            return
        if self.current_page_key == "clone":
            self.clone_page.pick_button.click()

    def trigger_context_delete(self) -> None:
        if self.current_page_key == "voices":
            index = self.voice_page.tabs.currentIndex()
            if index == 1:
                self.voice_page.cloned_delete_button.click()
            elif index == 0:
                self.voice_page.my_delete_button.click()
            return
        if self.current_page_key == "clone":
            self.clone_page.delete_clone_button.click()
            return
        if self.current_page_key == "history":
            self.history_page.delete_button.click()

    def trigger_context_switch_tab(self, index: int) -> None:
        if self.current_page_key == "voices" and index < self.voice_page.tabs.count():
            self.voice_page.tabs.setCurrentIndex(index)
            self.voice_page.tabs.tabBar().setFocus(Qt.ShortcutFocusReason)
            return
        if self.current_page_key == "studio" and index < self.studio_page.tabs.count():
            self.studio_page.tabs.setCurrentIndex(index)
            self.studio_page.tabs.tabBar().setFocus(Qt.ShortcutFocusReason)

    def refresh_all(self) -> None:
        client = self._require_client()
        if not client:
            return

        def task():
            return {
                "subscription": client.get_user_subscription(),
                "user": client.get_user(),
                "models": client.get_models(),
                "voices": client.list_all_voices(),
                "shared": client.get_shared_voices(page=1, page_size=18, category="professional"),
                "history": client.get_history(page_size=20).get("history", []),
            }

        self._start_task("Refreshing workspace...", task, self._on_workspace_loaded)

    def _on_workspace_loaded(self, bundle: dict) -> None:
        self.state.update(bundle)
        subscription = bundle.get("subscription") or {}
        models = bundle.get("models") or []
        voices = bundle.get("voices") or []
        history = bundle.get("history") or []
        self.dashboard_page.update_data(
            subscription=subscription,
            models=models,
            voices=voices,
            history=history,
        )
        self.voice_page.set_voices(voices)
        self.voice_page.set_shared_voices(bundle.get("shared") or {})
        self.clone_page.set_subscription(subscription)
        self.clone_page.set_cloned_voices(voices)
        self.studio_page.set_voice_options(voices)
        self.studio_page.set_model_options(models)
        self.history_page.set_history(history)
        if voices and self.voice_page.voice_table.currentRow() < 0:
            self.voice_page.voice_table.selectRow(0)
        message = f"Loaded {len(voices)} voices, {len(models)} models, {len(history)} history items."
        self._apply_api_state(message)
        self._announce_ui(message)

    def refresh_voices(self, search: str = "") -> None:
        client = self._require_client()
        if not client:
            return

        def task():
            return client.list_all_voices(search=search)

        self._start_task("Refreshing voices...", task, self._on_voices_loaded)

    def _on_voices_loaded(self, voices: list[dict]) -> None:
        self._apply_voice_inventory(voices)
        if voices:
            self.voice_page.voice_table.selectRow(0)
        message = f"Voice list updated: {len(voices)} items."
        self._apply_api_state(message)
        self._announce_ui(message)

    def refresh_shared_voices(self, filters: dict) -> None:
        client = self._require_client()
        if not client:
            return

        def task():
            return client.get_shared_voices(
                page=int(filters.get("page", 1) or 1),
                page_size=24,
                search=filters.get("search", ""),
                category=filters.get("category", ""),
                language=filters.get("language", ""),
                accent=filters.get("accent", ""),
                gender=filters.get("gender", ""),
                age=filters.get("age", ""),
            )

        self._start_task("Refreshing shared library...", task, self._on_shared_loaded)

    def _on_shared_loaded(self, payload: dict) -> None:
        self.state["shared"] = payload
        self.voice_page.set_shared_voices(payload)
        message = f"Shared voices loaded: {len(payload.get('voices', []))}."
        self.voice_page.show_library_feedback(message)
        self._apply_api_state(message)
        self._announce_ui(message)

    def load_voice_details(self, voice_id: str) -> None:
        client = self._require_client()
        if not client or not voice_id:
            return

        def task():
            try:
                return {"voice": client.get_voice(voice_id)}
            except ApiError as error:
                if self._is_missing_voice_error(error):
                    return {"missing_voice_ids": [voice_id]}
                raise

        self._start_task("Loading voice details...", task, self._on_voice_detail_loaded)

    def _on_voice_detail_loaded(self, payload: dict) -> None:
        if payload.get("missing_voice_ids"):
            self._queue_missing_voice_notice(self._prune_missing_voice_ids(payload.get("missing_voice_ids", [])))
            return
        voice = payload.get("voice") or {}
        self.state["selected_voice"] = voice
        scope = "cloned" if (voice.get("category") or "").lower() == "cloned" else "my"
        if not self.voice_page.is_single_voice_selected(scope, voice.get("voice_id", "")):
            return
        self.voice_page.set_selected_voice(voice, scope=scope)
        self._apply_api_state(f"Loaded voice: {voice.get('name', 'unknown')}.")

    def save_voice_metadata(self, payload: dict) -> None:
        client = self._require_client()
        if not client:
            return
        if not payload.get("voice_id") or not payload.get("name"):
            QMessageBox.warning(self, "Missing data", "Voice name and selection are required.")
            return

        def task():
            try:
                client.update_voice(
                    payload["voice_id"],
                    name=payload["name"],
                    description=payload.get("description", ""),
                    labels=parse_labels(payload.get("labels_text", "")),
                )
                return {
                    "voices": client.list_all_voices(search=self.voice_page.current_workspace_search()),
                    "voice": client.get_voice(payload["voice_id"]),
                }
            except ApiError as error:
                if self._is_missing_voice_error(error):
                    return {"missing_voice_ids": [payload["voice_id"]]}
                raise

        self._start_task("Saving voice metadata...", task, self._on_voice_mutation_loaded)

    def _on_voice_mutation_loaded(self, payload: dict) -> None:
        if payload.get("missing_voice_ids"):
            self._queue_missing_voice_notice(self._prune_missing_voice_ids(payload.get("missing_voice_ids", [])))
            return
        voices = payload.get("voices", [])
        voice = payload.get("voice")
        self._apply_voice_inventory(voices)
        scope = "cloned" if (voice.get("category") or "").lower() == "cloned" else "my"
        self.voice_page.set_selected_voice(voice, scope=scope)
        self.voice_page.show_voice_feedback("Voice metadata updated.")
        self._apply_api_state("Voice update completed.")
        self._announce_ui("Voice update completed.")

    def delete_voice(self, selection: object) -> None:
        client = self._require_client()
        voice_ids = self._normalize_ids(selection)
        if not client or not voice_ids:
            return
        count = len(voice_ids)
        confirmed = QMessageBox.question(
            self,
            "Delete voice" if count == 1 else "Delete voices",
            "Delete the selected voice from your ElevenLabs workspace?"
            if count == 1
            else f"Delete {count} selected voices from your ElevenLabs workspace?",
        )
        if confirmed != QMessageBox.Yes:
            return

        def task():
            deleted_count = 0
            missing_ids: list[str] = []
            failed_ids: list[str] = []
            for voice_id in voice_ids:
                try:
                    client.delete_voice(voice_id)
                    deleted_count += 1
                except ApiError as error:
                    if self._is_missing_voice_error(error):
                        missing_ids.append(voice_id)
                        continue
                    failed_ids.append(voice_id)
            return {
                "voices": client.list_all_voices(),
                "deleted_count": deleted_count,
                "missing_ids": missing_ids,
                "failed_ids": failed_ids,
                "requested_count": count,
            }

        self._start_task("Deleting voice..." if count == 1 else "Deleting voices...", task, self._on_voice_delete_loaded)

    def _on_voice_delete_loaded(self, payload: dict) -> None:
        voices = [
            voice
            for voice in payload.get("voices", [])
            if voice.get("voice_id", "") not in set(payload.get("missing_ids", []) or [])
        ]
        self._on_voices_loaded(voices)
        deleted_count = int(payload.get("deleted_count", 0) or 0)
        missing_count = len(payload.get("missing_ids", []) or [])
        failed_count = len(payload.get("failed_ids", []) or [])
        parts: list[str] = []
        if deleted_count:
            parts.append("Voice deleted." if deleted_count == 1 else f"Deleted {deleted_count} voices.")
        if missing_count:
            parts.append(
                "Skipped 1 voice that no longer exists."
                if missing_count == 1
                else f"Skipped {missing_count} voices that no longer exist."
            )
        if failed_count:
            parts.append(
                "1 voice could not be deleted."
                if failed_count == 1
                else f"{failed_count} voices could not be deleted."
            )
        message = " ".join(parts) or "No voices were deleted."
        self.voice_page.show_voice_feedback(message)
        self.clone_page.show_status(message)
        self._apply_api_state(message)
        self._announce_ui(message)
        if failed_count:
            QMessageBox.warning(
                self,
                "Some voices could not be deleted",
                message,
            )

    def add_shared_voice(self, payload: object) -> None:
        client = self._require_client()
        if not client:
            return
        payloads = payload if isinstance(payload, list) else [payload]
        payloads = [item for item in payloads if isinstance(item, dict)]
        if not payloads:
            return
        if any(not item.get("public_user_id") or not item.get("voice_id") or not item.get("new_name") for item in payloads):
            QMessageBox.warning(self, "Missing selection", "Select a shared voice and provide a local name.")
            return

        def task():
            for item in payloads:
                client.add_shared_voice(
                    public_user_id=item["public_user_id"],
                    voice_id=item["voice_id"],
                    new_name=item["new_name"],
                )
            return {"voices": client.list_all_voices(), "count": len(payloads), "name": payloads[0]["new_name"]}

        def on_success(result: dict) -> None:
            self._on_voices_loaded(result.get("voices", []))
            count = int(result.get("count", 0) or 0)
            message = (
                f"{result.get('name', 'Voice')} added to your voice library."
                if count == 1
                else f"Added {count} shared voices to your voice library."
            )
            self.voice_page.show_library_feedback(message)
            self._apply_api_state(message)
            self._announce_ui(message)

        label = "Adding shared voice..." if len(payloads) == 1 else "Adding shared voices..."
        self._start_task(label, task, on_success)

    def use_voice_in_studio(self, voice: dict) -> None:
        self.studio_page.route_voice(voice)
        self.switch_page("studio")
        message = f"{voice.get('name', 'Voice')} opened in Studio."
        self._apply_api_state(message)
        self._announce_ui(message)

    def create_clone(self, payload: dict) -> None:
        client = self._require_client()
        if not client:
            return
        if not payload.get("name") or not payload.get("sample_paths"):
            QMessageBox.warning(self, "Missing clone data", "Provide a name and at least one sample file.")
            return

        clone_type = payload.get("clone_type", "ivc")
        sample_paths = [Path(path) for path in payload.get("sample_paths", [])]

        self.clone_page.set_busy(True)
        self.clone_page.set_progress(0, "Preparing clone request...", "Validating sample set and clone metadata.", busy=True)
        self.last_clone_progress_percent = -1

        worker = Worker(
            lambda: self._run_clone_task(
                payload=payload,
                sample_paths=sample_paths,
                clone_type=clone_type,
                client=client,
                progress=lambda data: self._emit_worker_progress(worker, data),
                is_cancelled=lambda: worker.is_cancelled,
            )
        )
        self.clone_worker = worker
        self.pending_tasks += 1
        self._apply_api_state("Creating clone...")
        worker.signals.progress.connect(self._on_clone_progress)
        worker.signals.success.connect(self._on_clone_finished)
        worker.signals.error.connect(lambda message: self._handle_clone_error("Creating clone...", message))
        worker.signals.finished.connect(self._on_clone_task_finished)
        self.thread_pool.start(worker)

    def _run_clone_task(self, *, payload: dict, sample_paths: list[Path], clone_type: str, client: ElevenLabsClient, progress, is_cancelled):
        def checkpoint(percent: int, status: str, detail: str, *, beep: bool = True) -> None:
            progress({"percent": percent, "status": status, "detail": detail, "beep": beep})

        checkpoint(5, "Preparing clone request...", "Checking file list and selected clone type.")
        if is_cancelled():
            return {"cancelled": True}

        if clone_type == "pvc":
            checkpoint(20, "Creating professional clone shell...", "Saving metadata before samples are uploaded.")
            voice = client.create_pvc_voice(
                name=payload["name"],
                language=payload.get("language", "en"),
                description=payload.get("description", ""),
                labels=parse_labels(payload.get("labels_text", "")),
            )
            if is_cancelled():
                return {"cancelled": True}

            checkpoint(55, "Uploading PVC samples...", f"{len(sample_paths)} sample file(s) are being uploaded.")
            client.add_pvc_samples(
                voice["voice_id"],
                sample_paths=sample_paths,
                remove_background_noise=bool(payload.get("remove_background_noise", True)),
            )
            checkpoint(
                85,
                "Professional clone created.",
                "Samples uploaded. Use captcha verification and training controls to finish the PVC workflow.",
            )
        else:
            checkpoint(20, "Uploading samples...", f"{len(sample_paths)} sample file(s) are being sent for IVC.")
            voice = client.create_ivc_voice(
                name=payload["name"],
                sample_paths=sample_paths,
                description=payload.get("description", ""),
                labels=parse_labels(payload.get("labels_text", "")),
                remove_background_noise=bool(payload.get("remove_background_noise", True)),
            )
            checkpoint(85, "Instant clone created.", "The voice is ready and will appear in your cloned voices list.")

        if is_cancelled():
            return {"cancelled": True}

        checkpoint(95, "Refreshing voice library...", "Syncing the new clone with the workspace state.", beep=False)
        voices = client.list_all_voices()
        return {"cancelled": False, "voices": voices, "voice": voice, "clone_type": clone_type}

    def _emit_worker_progress(self, worker: Worker, payload: dict) -> None:
        try:
            worker.signals.progress.emit(payload)
        except RuntimeError:
            pass

    def _on_clone_progress(self, payload: dict) -> None:
        percent = int(payload.get("percent", 0))
        status = str(payload.get("status", "Working..."))
        detail = str(payload.get("detail", ""))
        self.clone_page.set_progress(percent, status, detail, busy=True)
        self._apply_api_state(status)
        self._announce_ui(f"{status} {detail}")
        if payload.get("beep") and percent != self.last_clone_progress_percent:
            QApplication.beep()
            self.last_clone_progress_percent = percent

    def _on_clone_finished(self, payload: dict) -> None:
        if payload.get("cancelled"):
            self.clone_page.show_status("Clone task cancelled.")
            self._announce_ui("Clone task cancelled.")
            return

        voices = payload.get("voices", [])
        self._on_voices_loaded(voices)
        voice = payload.get("voice") or {}
        clone_type = str(payload.get("clone_type", "ivc"))
        if clone_type == "pvc":
            message = f"PVC draft ready: {voice.get('name', 'New voice')}. Fetch captcha and train it from Clone Lab."
        else:
            message = f"IVC clone ready: {voice.get('name', 'New voice')}."
        self.clone_page.set_progress(100, "Clone flow finished.", message, busy=False)
        self.clone_page.show_status(message)
        self._apply_api_state(message)
        self._announce_ui(message)

    def cancel_clone_task(self) -> None:
        if self.clone_worker:
            self.clone_worker.cancel()
            self.clone_page.set_progress(
                self.last_clone_progress_percent if self.last_clone_progress_percent >= 0 else 0,
                "Cancelling clone task...",
                "The current request cannot always be interrupted server-side, but the UI will stop waiting for later stages.",
                busy=True,
            )

    def _handle_clone_error(self, label: str, message: str) -> None:
        summary = message.splitlines()[0]
        self.clone_page.set_progress(0, "Clone flow failed.", summary, busy=False)
        self.clone_page.show_status(summary)
        self._handle_task_error(label, message)

    def _on_clone_task_finished(self) -> None:
        self.clone_page.set_busy(False)
        self.clone_worker = None
        self.pending_tasks = max(0, self.pending_tasks - 1)
        if self.pending_tasks == 0:
            self._apply_api_state("Ready.")

    def fetch_pvc_captcha(self, voice_id: str) -> None:
        client = self._require_client()
        if not client or not voice_id:
            return

        def task():
            return client.get_pvc_verification_captcha(voice_id)

        def on_success(payload: BinaryPayload) -> None:
            suffix = content_type_to_suffix(payload.content_type)
            path = timestamped_file(self.config.cache_dir, f"pvc-captcha-{voice_id}", suffix)
            path.write_bytes(payload.content)
            message = f"Captcha saved to {path.name}. Read it, record it, then choose the recording below."
            self.clone_page.set_captcha_status(message)
            self._apply_api_state("PVC captcha ready.")
            self._announce_ui(message)

        self._start_task("Fetching PVC captcha...", task, on_success)

    def verify_pvc_captcha(self, payload: dict) -> None:
        client = self._require_client()
        if not client:
            return
        voice_id = payload.get("voice_id", "")
        recording_path = payload.get("recording_path", "")
        if not voice_id or not recording_path:
            QMessageBox.warning(self, "Missing verification data", "Select a professional clone and a verification recording.")
            return

        def task():
            return client.verify_pvc_captcha(voice_id, recording_path=Path(recording_path))

        def on_success(_result: dict) -> None:
            message = "PVC owner verification submitted successfully."
            self.clone_page.set_captcha_status(message)
            self._apply_api_state(message)
            self._announce_ui(message)
            self.refresh_voices()

        self._start_task("Submitting PVC verification...", task, on_success)

    def train_pvc_voice(self, payload: dict) -> None:
        client = self._require_client()
        if not client:
            return
        if not payload.get("voice_id"):
            QMessageBox.warning(self, "Missing voice", "Select a professional clone first.")
            return

        def task():
            client.start_pvc_training(payload["voice_id"], model_id=payload.get("model_id", "eleven_multilingual_v2"))
            return client.list_all_voices()

        def on_success(voices: list[dict]) -> None:
            self._on_voices_loaded(voices)
            message = "PVC training started. Progress will appear in the cloned voices list after refresh."
            self.clone_page.set_captcha_status(message)
            self._apply_api_state(message)
            self._announce_ui(message)

        self._start_task("Starting PVC training...", task, on_success)

    def generate_tts(self, payload: dict) -> None:
        client = self._require_client()
        if not client:
            return
        if not payload.get("voice_id") or not payload.get("model_id") or not payload.get("text"):
            QMessageBox.warning(self, "Missing TTS data", "Voice, model and text are required.")
            return
        self.last_generation_request = {"kind": "tts", "payload": payload.copy()}
        self.studio_page.clear_result()
        self.studio_page.show_status("Generating speech...")

        def task():
            try:
                return {"audio": client.text_to_speech(**payload)}
            except ApiError as error:
                if self._is_missing_voice_error(error):
                    return {"missing_voice_ids": [payload.get("voice_id", "")]}
                raise

        self._start_task("Generating speech...", task, lambda result: self._on_audio_generation_result("tts", result))

    def generate_sts(self, payload: dict) -> None:
        client = self._require_client()
        if not client:
            return
        if not payload.get("voice_id") or not payload.get("model_id") or not payload.get("audio_path"):
            QMessageBox.warning(self, "Missing STS data", "Voice, model and source audio are required.")
            return
        self.last_generation_request = {"kind": "sts", "payload": payload.copy()}
        self.studio_page.clear_result()
        self.studio_page.show_status("Converting source audio...")

        def task():
            request = payload.copy()
            request["audio_path"] = Path(request["audio_path"])
            try:
                return {"audio": client.speech_to_speech(**request)}
            except ApiError as error:
                if self._is_missing_voice_error(error):
                    return {"missing_voice_ids": [payload.get("voice_id", "")]}
                raise

        self._start_task("Converting audio...", task, lambda result: self._on_audio_generation_result("sts", result))

    def _on_audio_generation_result(self, prefix: str, payload: dict) -> None:
        if payload.get("missing_voice_ids"):
            self._queue_missing_voice_notice(self._prune_missing_voice_ids(payload.get("missing_voice_ids", [])))
            return
        audio = payload.get("audio")
        if isinstance(audio, AudioPayload):
            self._on_audio_generated(prefix, audio)

    def _on_audio_generated(self, prefix: str, audio: AudioPayload) -> None:
        suffix = content_type_to_suffix(audio.content_type)
        path = timestamped_file(self.config.outputs_dir, prefix, suffix)
        path.write_bytes(audio.audio)
        meta = f"{audio.content_type} | req: {audio.request_id or 'n/a'} | chars: {audio.character_count or 'n/a'}"
        self.set_audio_source(str(path), is_local=True)
        self.studio_page.set_result(path.name, meta)
        message = f"Audio saved to {path.name}."
        self.studio_page.show_status(message)
        self._apply_api_state(message)
        self._announce_ui(message)
        self.replay_current_audio()
        self.refresh_history({"search": "", "source": ""})

    def replay_current_audio(self) -> None:
        if not self.current_audio_target:
            return
        if self.current_audio_is_local:
            url = QUrl.fromLocalFile(self.current_audio_target)
        else:
            url = QUrl(self.current_audio_target)
        if self.player.source() != url:
            self.player.setSource(url)
        else:
            self.player.setPosition(0)
        self.player.play()

    def regenerate_last_audio(self) -> None:
        if not self.last_generation_request:
            QMessageBox.information(self, "Nothing to regenerate", "Generate audio at least once before using Regenerate.")
            return
        kind = self.last_generation_request.get("kind")
        payload = dict(self.last_generation_request.get("payload") or {})
        if kind == "tts":
            self.generate_tts(payload)
        elif kind == "sts":
            self.generate_sts(payload)

    def download_current_audio(self) -> None:
        if not self.current_audio_is_local or not self.current_audio_target:
            QMessageBox.information(self, "Nothing to download", "Generate audio first to download it.")
            return
        source_path = Path(self.current_audio_target)
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save generated audio",
            str(self.config.outputs_dir / source_path.name),
            "Audio Files (*.mp3 *.wav *.ogg *.pcm *.bin)",
        )
        if not file_name:
            return
        Path(file_name).write_bytes(source_path.read_bytes())
        message = f"Downloaded audio to {Path(file_name).name}."
        self.studio_page.show_status(message)
        self._apply_api_state(message)
        self._announce_ui(message)

    def refresh_history(self, filters: dict) -> None:
        client = self._require_client()
        if not client:
            return

        def task():
            result = client.get_history(
                page_size=20,
                search=filters.get("search", ""),
                source=filters.get("source", ""),
            )
            return result.get("history", [])

        self._start_task("Refreshing history...", task, self._on_history_loaded)

    def _on_history_loaded(self, history_rows: list[dict]) -> None:
        self.state["history"] = history_rows
        self.history_page.set_history(history_rows)
        message = f"History updated: {len(history_rows)} items."
        self._apply_api_state(message)
        self._announce_ui(message)

    def play_history_audio(self, history_item_id: str) -> None:
        client = self._require_client()
        if not client or not history_item_id:
            return

        def task():
            return client.get_history_audio(history_item_id)

        self._start_task(
            "Downloading history audio...",
            task,
            lambda audio: self._on_history_audio_ready(history_item_id, audio, play_now=True),
        )

    def download_history_audio(self, selection: object) -> None:
        client = self._require_client()
        history_item_ids = self._normalize_ids(selection)
        if not client or not history_item_ids:
            return
        if len(history_item_ids) == 1:
            history_item_id = history_item_ids[0]

            def task():
                return client.get_history_audio(history_item_id)

            self._start_task(
                "Preparing download...",
                task,
                lambda audio: self._on_history_audio_ready(history_item_id, audio, play_now=False),
            )
            return

        target_dir = QFileDialog.getExistingDirectory(self, "Choose a folder for the selected history items")
        if not target_dir:
            return

        def task():
            downloads = []
            for history_item_id in history_item_ids:
                downloads.append((history_item_id, client.get_history_audio(history_item_id)))
            return downloads

        def on_success(downloads: list[tuple[str, AudioPayload]]) -> None:
            destination = Path(target_dir)
            for history_item_id, audio in downloads:
                suffix = content_type_to_suffix(audio.content_type)
                (destination / f"history-{history_item_id}{suffix}").write_bytes(audio.audio)
            message = f"Downloaded {len(downloads)} history items to {destination.name}."
            self._apply_api_state(message)
            self._announce_ui(message)

        self._start_task("Preparing downloads...", task, on_success)

    def _on_history_audio_ready(self, history_item_id: str, audio: AudioPayload, *, play_now: bool) -> None:
        suffix = content_type_to_suffix(audio.content_type)
        temp_path = timestamped_file(self.config.cache_dir, f"history-{history_item_id}", suffix)
        temp_path.write_bytes(audio.audio)
        if play_now:
            self.set_audio_source(str(temp_path), is_local=True)
            self.play_current_audio()
        else:
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save history audio",
                str(self.config.outputs_dir / temp_path.name),
                "Audio Files (*.mp3 *.wav *.ogg *.bin)",
            )
            if file_name:
                Path(file_name).write_bytes(audio.audio)
                message = f"Downloaded history audio to {Path(file_name).name}."
                self._apply_api_state(message)
                self._announce_ui(message)

    def delete_history_item(self, selection: object) -> None:
        client = self._require_client()
        history_item_ids = self._normalize_ids(selection)
        if not client or not history_item_ids:
            return
        count = len(history_item_ids)
        confirmed = QMessageBox.question(
            self,
            "Delete history item" if count == 1 else "Delete history items",
            "Delete the selected history record?"
            if count == 1
            else f"Delete {count} selected history records?",
        )
        if confirmed != QMessageBox.Yes:
            return
        filters = self.history_page.current_filters()

        def task():
            for history_item_id in history_item_ids:
                client.delete_history_item(history_item_id)
            result = client.get_history(
                page_size=20,
                search=filters.get("search", ""),
                source=filters.get("source", ""),
            )
            return {"history": result.get("history", []), "deleted_count": count}

        label = "Deleting history item..." if count == 1 else "Deleting history items..."
        self._start_task(label, task, self._on_history_delete_loaded)

    def _on_history_delete_loaded(self, payload: dict) -> None:
        self._on_history_loaded(payload.get("history", []))
        count = int(payload.get("deleted_count", 0) or 0)
        message = "History item deleted." if count == 1 else f"Deleted {count} history items."
        self._apply_api_state(message)
        self._announce_ui(message)

    def store_api_key(self, api_key: str) -> None:
        api_key = api_key.strip()
        if not api_key:
            QMessageBox.warning(self, "Missing key", "Enter an API key before saving.")
            return
        source_label = save_api_key(api_key)
        self.config.api_key = api_key
        self.config.api_key_source = source_label
        if self.client:
            self.client.set_api_key(api_key)
        else:
            self.client = ElevenLabsClient(api_key)
        self.sidebar_source.setText(f"Key source: {self.config.api_key_source}")
        self.settings_page.set_api_state(
            key_value=api_key,
            source=self.config.api_key_source,
            status=f"Saved to {source_label}.",
            spoken_fallback=self.settings_page.spoken_fallback.isChecked(),
        )
        self._apply_api_state("API key saved.")
        self._announce_ui("API key saved.")

    def test_api_key(self, api_key: str) -> None:
        candidate = api_key.strip() or self.config.api_key
        if not candidate:
            QMessageBox.warning(self, "Missing key", "Enter an API key first.")
            return

        def task():
            temp_client = ElevenLabsClient(candidate)
            try:
                return temp_client.get_user_subscription()
            finally:
                temp_client.close()

        self._start_task("Testing API key...", task, self._on_api_test_success)

    def _on_api_test_success(self, subscription: dict) -> None:
        self.settings_page.status_label.setText(
            f"Connection OK. Tier: {subscription.get('tier', 'unknown')}, status: {subscription.get('status', 'unknown')}."
        )
        self._apply_api_state("API connection verified.")
        self._announce_ui("API connection verified.")

    def play_remote_preview(self, title: str, url: str) -> None:
        if not url:
            return
        self.set_audio_source(url, is_local=False)
        self.play_current_audio()
        self._apply_api_state(f"Playing preview: {title}.")

    def play_local_sample_preview(self, path: str) -> None:
        if not path:
            return
        self.set_audio_source(path, is_local=True)
        self.play_current_audio()
        self._apply_api_state(f"Playing sample: {Path(path).name}.")

    def set_audio_source(self, target: str, *, is_local: bool) -> None:
        self.current_audio_target = target
        self.current_audio_is_local = is_local

    def play_current_audio(self) -> None:
        if not self.current_audio_target:
            return
        if self.current_audio_is_local:
            url = QUrl.fromLocalFile(self.current_audio_target)
        else:
            url = QUrl(self.current_audio_target)
        if self.player.source() != url:
            self.player.setSource(url)
        self.player.play()

    def open_audio_folder(self) -> None:
        if self.current_audio_is_local and self.current_audio_target:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.current_audio_target).parent)))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.config.outputs_dir)))
