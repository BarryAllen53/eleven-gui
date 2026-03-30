from __future__ import annotations

from collections import OrderedDict

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from eleven_gui.accessibility import AccessibleTabWidget, configure_focusable_text_edit, defer_tab_order_chain
from eleven_gui.ui.widgets import AccessibleListWidget, MetricCard, SectionCard, build_icon
from eleven_gui.utils import format_labels


def _voice_language(voice: dict) -> str:
    fine_tuning = voice.get("fine_tuning") or {}
    labels = voice.get("labels") or {}
    verified_languages = voice.get("verified_languages") or []
    for candidate in (
        fine_tuning.get("language"),
        labels.get("language"),
        verified_languages[0].get("language") if verified_languages else "",
    ):
        if candidate:
            return str(candidate)
    return ""


def _voice_label(voice: dict, key: str) -> str:
    labels = voice.get("labels") or {}
    value = labels.get(key)
    return str(value) if value else ""


def _voice_matches_text(voice: dict, search: str) -> bool:
    if not search:
        return True
    text = search.casefold()
    haystack = " ".join(
        [
            voice.get("name", ""),
            voice.get("description", "") or "",
            format_labels(voice.get("labels") or {}),
            _voice_language(voice),
        ]
    ).casefold()
    return text in haystack


class VoiceHubPage(QWidget):
    refresh_voices_requested = Signal(str)
    refresh_shared_requested = Signal(object)
    voice_selected = Signal(str)
    preview_requested = Signal(str, str)
    save_metadata_requested = Signal(object)
    delete_voice_requested = Signal(object)
    add_shared_requested = Signal(object)
    use_voice_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.voices: list[dict] = []
        self.my_voices: list[dict] = []
        self.cloned_voices: list[dict] = []
        self.shared_voices: list[dict] = []
        self.filtered_my_voices: list[dict] = []
        self.filtered_cloned_voices: list[dict] = []
        self.filtered_shared_voices: list[dict] = []
        self.setAccessibleName("Voice Hub page")
        self.setAccessibleDescription("Manage your saved voices, cloned voices, and shared library imports.")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(18)

        title = QLabel("Voice Hub")
        title.setProperty("role", "title")
        subtitle = QLabel(
            "Browse, clean up and route voices with less clutter. Library imports, cloned voices and metadata editing stay separated."
        )
        subtitle.setProperty("role", "muted")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        self.page_status = QLabel("Filter first, then open a voice in Studio, import it from the library or update metadata.")
        self.page_status.setProperty("role", "muted")
        self.page_status.setAccessibleName("Voice Hub status")
        self.page_status.setWordWrap(True)
        root.addWidget(self.page_status)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(14)
        self.my_summary_card = MetricCard("My Voices", "0", "Saved and ready to route")
        self.cloned_summary_card = MetricCard("Cloned Voices", "0", "Instant and professional clones")
        self.library_summary_card = MetricCard("Library Results", "0", "Shared voices matching current query")
        summary_row.addWidget(self.my_summary_card)
        summary_row.addWidget(self.cloned_summary_card)
        summary_row.addWidget(self.library_summary_card)
        root.addLayout(summary_row)

        self.tabs = AccessibleTabWidget(
            "Voice Hub sections",
            "Switch between your voices, cloned voices, and the shared library.",
        )
        self.tabs.addTab(self._build_my_voices_tab(), "&My Voices")
        self.tabs.addTab(self._build_cloned_voices_tab(), "&Cloned Voices")
        self.tabs.addTab(self._build_library_tab(), "Voice &Library")
        root.addWidget(self.tabs, 1)
        self.initial_focus_widget = self.tabs.tabBar()

    def _build_voice_filters(self, prefix: str) -> tuple[QWidget, dict[str, QWidget]]:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        search = QLineEdit()
        search.setPlaceholderText("Search voices")
        language = QComboBox()
        accent = QComboBox()
        gender = QComboBox()
        age = QComboBox()
        use_case = QComboBox()

        for combo, name in (
            (language, "Language"),
            (accent, "Accent"),
            (gender, "Gender"),
            (age, "Age"),
            (use_case, "Use case"),
        ):
            combo.addItem(f"All {name.lower()}", "")

        widgets = {
            "search": search,
            "language": language,
            "accent": accent,
            "gender": gender,
            "age": age,
            "use_case": use_case,
        }
        for key, widget in widgets.items():
            setattr(self, f"{prefix}_{key}", widget)
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda _value="", tab=prefix: self._apply_voice_filters(tab))
            else:
                widget.currentIndexChanged.connect(lambda _index=0, tab=prefix: self._apply_voice_filters(tab))

        search.setAccessibleName(f"{prefix.replace('_', ' ')} search")
        language.setAccessibleName(f"{prefix.replace('_', ' ')} language filter")
        accent.setAccessibleName(f"{prefix.replace('_', ' ')} accent filter")
        gender.setAccessibleName(f"{prefix.replace('_', ' ')} gender filter")
        age.setAccessibleName(f"{prefix.replace('_', ' ')} age filter")
        use_case.setAccessibleName(f"{prefix.replace('_', ' ')} use case filter")

        layout.addWidget(search, 2)
        layout.addWidget(language)
        layout.addWidget(accent)
        layout.addWidget(gender)
        layout.addWidget(age)
        layout.addWidget(use_case)
        return bar, widgets

    def _build_workspace_detail_card(self, title_text: str, cloned_scope: bool) -> SectionCard:
        card = SectionCard()
        card.setAccessibleName(f"{title_text} detail editor")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel(title_text)
        title.setProperty("role", "section-title")
        selected_label = QLabel("No voice selected.")
        selected_label.setProperty("role", "muted")
        selected_label.setWordWrap(True)
        usage_hint = QLabel("Use This Voice opens the Studio page with this voice preselected.")
        usage_hint.setProperty("role", "muted")
        usage_hint.setWordWrap(True)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        name = QLineEdit()
        description = QTextEdit()
        description.setFixedHeight(88)
        configure_focusable_text_edit(
            description,
            name=f"{title_text} description",
            description="Press Tab to move to the next control.",
        )
        labels = QLineEdit()
        labels.setPlaceholderText("locale:tr, mood:warm")
        name_label = QLabel("&Name")
        name_label.setBuddy(name)
        description_label = QLabel("&Description")
        description_label.setBuddy(description)
        labels_label = QLabel("La&bels")
        labels_label.setBuddy(labels)
        form.addRow(name_label, name)
        form.addRow(description_label, description)
        form.addRow(labels_label, labels)

        feedback = QLabel("No pending changes.")
        feedback.setProperty("role", "muted")
        feedback.setWordWrap(True)

        button_row = QHBoxLayout()
        preview = QPushButton("&Preview")
        preview.setIcon(build_icon("play"))
        use_button = QPushButton("&Use This Voice")
        use_button.setProperty("variant", "primary")
        use_button.setIcon(build_icon("link"))
        save = QPushButton("Save &Metadata")
        delete = QPushButton("&Delete Voice")
        delete.setProperty("variant", "danger")
        button_row.addWidget(preview)
        button_row.addWidget(use_button)
        button_row.addWidget(save)
        button_row.addWidget(delete)

        scope = "cloned" if cloned_scope else "my"
        setattr(self, f"{scope}_selected_voice_label", selected_label)
        setattr(self, f"{scope}_usage_hint", usage_hint)
        setattr(self, f"{scope}_voice_name", name)
        setattr(self, f"{scope}_voice_description", description)
        setattr(self, f"{scope}_voice_labels", labels)
        setattr(self, f"{scope}_feedback", feedback)
        setattr(self, f"{scope}_preview_button", preview)
        setattr(self, f"{scope}_use_voice_button", use_button)
        setattr(self, f"{scope}_save_meta_button", save)
        setattr(self, f"{scope}_delete_button", delete)

        preview.clicked.connect(lambda: self._preview_workspace_voice(scope))
        use_button.clicked.connect(lambda: self._emit_use_voice(scope))
        save.clicked.connect(lambda: self._emit_save_metadata(scope))
        delete.clicked.connect(lambda: self._emit_delete_voice(scope))

        layout.addWidget(title)
        layout.addWidget(selected_label)
        layout.addWidget(usage_hint)
        layout.addLayout(form)
        layout.addWidget(feedback)
        layout.addLayout(button_row)
        self._set_workspace_actions_for_selection(scope, [])
        return card

    def _build_my_voices_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        filters_bar, widgets = self._build_voice_filters("my")
        self.my_refresh_button = QPushButton("&Refresh Voices")
        self.my_refresh_button.setIcon(build_icon("refresh"))
        self.my_refresh_button.clicked.connect(lambda: self.refresh_voices_requested.emit(self.my_search.text().strip()))
        filters_layout = filters_bar.layout()
        assert isinstance(filters_layout, QHBoxLayout)
        filters_layout.addWidget(self.my_refresh_button)

        body = QHBoxLayout()
        body.setSpacing(14)
        self.voice_list = AccessibleListWidget("My voices list", multi_select=True)
        self.voice_table = self.voice_list
        self.voice_list.itemSelectionChanged.connect(lambda: self._emit_workspace_voice_selected("my"))
        detail_card = self._build_workspace_detail_card("Selected Voice", cloned_scope=False)
        body.addWidget(self.voice_list, 3)
        body.addWidget(detail_card, 2)

        layout.addWidget(filters_bar)
        layout.addLayout(body, 1)
        defer_tab_order_chain(
            tab,
            self.tabs.tabBar(),
            widgets["search"],
            widgets["language"],
            widgets["accent"],
            widgets["gender"],
            widgets["age"],
            widgets["use_case"],
            self.my_refresh_button,
            self.voice_list,
            self.my_voice_name,
            self.my_voice_description,
            self.my_voice_labels,
            self.my_preview_button,
            self.my_use_voice_button,
            self.my_save_meta_button,
            self.my_delete_button,
        )
        return tab

    def _build_cloned_voices_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        filters_bar, widgets = self._build_voice_filters("cloned")
        self.cloned_refresh_button = QPushButton("Refresh &Clones")
        self.cloned_refresh_button.setIcon(build_icon("refresh"))
        self.cloned_refresh_button.clicked.connect(lambda: self.refresh_voices_requested.emit(self.cloned_search.text().strip()))
        filters_layout = filters_bar.layout()
        assert isinstance(filters_layout, QHBoxLayout)
        filters_layout.addWidget(self.cloned_refresh_button)

        body = QHBoxLayout()
        body.setSpacing(14)
        self.cloned_list = AccessibleListWidget("Cloned voices list", multi_select=True)
        self.cloned_list.itemSelectionChanged.connect(lambda: self._emit_workspace_voice_selected("cloned"))
        detail_card = self._build_workspace_detail_card("Selected Cloned Voice", cloned_scope=True)
        body.addWidget(self.cloned_list, 3)
        body.addWidget(detail_card, 2)

        layout.addWidget(filters_bar)
        layout.addLayout(body, 1)
        defer_tab_order_chain(
            tab,
            self.tabs.tabBar(),
            widgets["search"],
            widgets["language"],
            widgets["accent"],
            widgets["gender"],
            widgets["age"],
            widgets["use_case"],
            self.cloned_refresh_button,
            self.cloned_list,
            self.cloned_voice_name,
            self.cloned_voice_description,
            self.cloned_voice_labels,
            self.cloned_preview_button,
            self.cloned_use_voice_button,
            self.cloned_save_meta_button,
            self.cloned_delete_button,
        )
        return tab

    def _build_library_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        filters = QWidget()
        filters_layout = QHBoxLayout(filters)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(10)
        self.library_search = QLineEdit()
        self.library_search.setPlaceholderText("Search shared voices")
        self.library_category = QComboBox()
        self.library_category.addItems(["All categories", "professional", "high_quality", "generated", "voice_design"])
        self.library_language = QLineEdit()
        self.library_language.setPlaceholderText("Language code")
        self.library_accent = QLineEdit()
        self.library_accent.setPlaceholderText("Accent")
        self.library_gender = QComboBox()
        self.library_gender.addItems(["All genders", "male", "female", "non_binary"])
        self.library_age = QComboBox()
        self.library_age.addItems(["All ages", "young", "middle_aged", "old"])
        self.library_refresh_button = QPushButton("Refresh &Library")
        self.library_refresh_button.setIcon(build_icon("refresh"))
        self.library_refresh_button.clicked.connect(self._emit_shared_refresh)
        for widget in (
            self.library_search,
            self.library_category,
            self.library_language,
            self.library_accent,
            self.library_gender,
            self.library_age,
        ):
            filters_layout.addWidget(widget)
        filters_layout.addWidget(self.library_refresh_button)

        self.library_list = AccessibleListWidget("Shared voices list", multi_select=True)
        self.library_table = self.library_list
        self.library_list.itemSelectionChanged.connect(self._update_library_hint)

        footer = SectionCard()
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(18, 18, 18, 18)
        footer_layout.setSpacing(10)
        footer_title = QLabel("Add Shared Voice")
        footer_title.setProperty("role", "section-title")
        self.library_hint = QLabel("Select a shared voice to add it into your collection.")
        self.library_hint.setProperty("role", "muted")
        self.library_hint.setWordWrap(True)
        self.new_shared_name = QLineEdit()
        self.new_shared_name.setPlaceholderText("Local name for the imported voice")
        self.library_feedback = QLabel("No import has been started yet.")
        self.library_feedback.setProperty("role", "muted")
        self.library_feedback.setWordWrap(True)
        footer_buttons = QHBoxLayout()
        self.library_preview_button = QPushButton("&Preview")
        self.library_preview_button.setIcon(build_icon("play"))
        self.library_preview_button.clicked.connect(self._preview_selected_shared_voice)
        self.add_shared_button = QPushButton("&Add Shared Voice")
        self.add_shared_button.setProperty("variant", "primary")
        self.add_shared_button.clicked.connect(self._emit_add_shared)
        footer_buttons.addWidget(self.library_preview_button)
        footer_buttons.addWidget(self.add_shared_button)
        footer_buttons.addStretch(1)
        footer_layout.addWidget(footer_title)
        footer_layout.addWidget(self.library_hint)
        footer_layout.addWidget(self.new_shared_name)
        footer_layout.addWidget(self.library_feedback)
        footer_layout.addLayout(footer_buttons)

        layout.addWidget(filters)
        layout.addWidget(self.library_list, 1)
        layout.addWidget(footer)
        defer_tab_order_chain(
            tab,
            self.tabs.tabBar(),
            self.library_search,
            self.library_category,
            self.library_language,
            self.library_accent,
            self.library_gender,
            self.library_age,
            self.library_refresh_button,
            self.library_list,
            self.new_shared_name,
            self.library_preview_button,
            self.add_shared_button,
        )
        self._set_library_actions_for_selection([])
        return tab

    def set_voices(self, voices: list[dict]) -> None:
        self.voices = voices
        self.my_voices = [voice for voice in voices if (voice.get("category") or "").lower() != "cloned"]
        self.cloned_voices = [voice for voice in voices if (voice.get("category") or "").lower() == "cloned"]
        self.my_summary_card.set_content(str(len(self.my_voices)), "Saved and ready to route")
        self.cloned_summary_card.set_content(str(len(self.cloned_voices)), "Instant and professional clones")
        self._populate_voice_filter_options("my", self.my_voices)
        self._populate_voice_filter_options("cloned", self.cloned_voices)
        self._apply_voice_filters("my")
        self._apply_voice_filters("cloned")
        if not voices:
            self.set_selected_voice(None, scope="my")
            self.set_selected_voice(None, scope="cloned")

    def set_selected_voice(self, voice: dict | None, *, scope: str) -> None:
        prefix = "my" if scope == "my" else "cloned"
        selected_label = getattr(self, f"{prefix}_selected_voice_label")
        name = getattr(self, f"{prefix}_voice_name")
        description = getattr(self, f"{prefix}_voice_description")
        labels = getattr(self, f"{prefix}_voice_labels")
        feedback = getattr(self, f"{prefix}_feedback")
        if not voice:
            selected_label.setText("No voice selected.")
            name.clear()
            description.clear()
            labels.clear()
            feedback.setText("Select a voice to edit metadata or open it in Studio.")
            self._set_workspace_actions_for_selection(prefix, [])
            return

        details = [
            voice.get("name", "Unknown"),
            f"type: {voice.get('category', 'n/a')}",
            f"language: {_voice_language(voice) or 'n/a'}",
            f"accent: {_voice_label(voice, 'accent') or 'n/a'}",
            f"id: {voice.get('voice_id', '')}",
        ]
        selected_label.setText(" | ".join(details))
        name.setText(voice.get("name", ""))
        description.setPlainText(voice.get("description") or "")
        labels.setText(format_labels(voice.get("labels") or {}))
        feedback.setText("Metadata changes are local until you press Save Metadata.")
        self._set_workspace_actions_for_selection(prefix, [voice])

    def set_shared_voices(self, payload: dict) -> None:
        self.shared_voices = payload.get("voices", [])
        self.filtered_shared_voices = list(self.shared_voices)
        items = [self._shared_item_text(voice) for voice in self.filtered_shared_voices]
        self.library_list.set_items(items)
        self.library_summary_card.set_content(str(len(self.filtered_shared_voices)), "Shared voices matching current query")
        self._update_library_hint()

    def show_voice_feedback(self, text: str) -> None:
        current_tab = self.tabs.currentIndex()
        if current_tab == 1:
            self.cloned_feedback.setText(text)
        else:
            self.my_feedback.setText(text)
        self.page_status.setText(text)

    def show_library_feedback(self, text: str) -> None:
        self.library_feedback.setText(text)
        self.page_status.setText(text)

    def current_workspace_search(self) -> str:
        index = self.tabs.currentIndex()
        if index == 1:
            return self.cloned_search.text().strip()
        if index == 0:
            return self.my_search.text().strip()
        return ""

    def is_single_voice_selected(self, scope: str, voice_id: str) -> bool:
        selected = self._selected_workspace_voices(scope)
        return len(selected) == 1 and selected[0].get("voice_id", "") == voice_id

    def _emit_workspace_voice_selected(self, scope: str) -> None:
        selected = self._selected_workspace_voices(scope)
        if len(selected) == 1:
            self._set_workspace_actions_for_selection(scope, selected)
            self.voice_selected.emit(selected[0].get("voice_id", ""))
            return
        if selected:
            self._show_workspace_multi_selection(scope, selected)
            return
        self.set_selected_voice(None, scope=scope)

    def _emit_save_metadata(self, scope: str) -> None:
        selected = self._selected_workspace_voices(scope)
        voice = selected[0] if len(selected) == 1 else None
        if not voice:
            return
        prefix = "my" if scope == "my" else "cloned"
        self.save_metadata_requested.emit(
            {
                "voice_id": voice.get("voice_id", ""),
                "name": getattr(self, f"{prefix}_voice_name").text().strip(),
                "description": getattr(self, f"{prefix}_voice_description").toPlainText().strip(),
                "labels_text": getattr(self, f"{prefix}_voice_labels").text().strip(),
            }
        )

    def _emit_delete_voice(self, scope: str) -> None:
        selected = self._selected_workspace_voices(scope)
        if selected:
            self.delete_voice_requested.emit([voice.get("voice_id", "") for voice in selected if voice.get("voice_id")])

    def _emit_use_voice(self, scope: str) -> None:
        voice = self._primary_workspace_voice(scope)
        if voice:
            self.use_voice_requested.emit(voice)

    def _emit_shared_refresh(self) -> None:
        self.refresh_shared_requested.emit(
            {
                "search": self.library_search.text().strip(),
                "category": "" if self.library_category.currentIndex() == 0 else self.library_category.currentText().strip(),
                "language": self.library_language.text().strip(),
                "accent": self.library_accent.text().strip(),
                "gender": "" if self.library_gender.currentIndex() == 0 else self.library_gender.currentText().strip(),
                "age": "" if self.library_age.currentIndex() == 0 else self.library_age.currentText().strip(),
                "page": 1,
            }
        )

    def _emit_add_shared(self) -> None:
        shared_voices = self._selected_shared_voices()
        if not shared_voices:
            return
        if len(shared_voices) == 1:
            shared = shared_voices[0]
            self.add_shared_requested.emit(
                {
                    "public_user_id": shared.get("public_owner_id", ""),
                    "voice_id": shared.get("voice_id", ""),
                    "new_name": self.new_shared_name.text().strip() or shared.get("name", "Imported Voice"),
                }
            )
            return
        payload = []
        for shared in shared_voices:
            payload.append(
                {
                    "public_user_id": shared.get("public_owner_id", ""),
                    "voice_id": shared.get("voice_id", ""),
                    "new_name": shared.get("name", "Imported Voice"),
                }
            )
        self.add_shared_requested.emit(payload)

    def _preview_workspace_voice(self, scope: str) -> None:
        voice = self._primary_workspace_voice(scope)
        if voice and voice.get("preview_url"):
            self.preview_requested.emit(voice.get("name", "Voice Preview"), voice.get("preview_url", ""))

    def _preview_selected_shared_voice(self) -> None:
        voice = self._primary_shared_voice()
        if voice and voice.get("preview_url"):
            self.preview_requested.emit(voice.get("name", "Shared Voice Preview"), voice.get("preview_url", ""))

    def _update_library_hint(self) -> None:
        selected = self._selected_shared_voices()
        self._set_library_actions_for_selection(selected)
        if not selected:
            self.library_hint.setText("Select a shared voice to add it into your collection.")
            return
        if len(selected) > 1:
            self.library_hint.setText(
                f"{len(selected)} shared voices selected. Preview uses the first selection. "
                "Add Shared Voice imports all selected voices using their library names."
            )
            return
        shared = selected[0]
        self.library_hint.setText(
            f"{shared.get('name', 'Unknown')} | {shared.get('category', 'n/a')} | "
            f"{shared.get('language', 'n/a')} | accent: {shared.get('accent', 'n/a')} | "
            f"cloned {shared.get('cloned_by_count', 0)} times."
        )
        if not self.new_shared_name.text().strip():
            self.new_shared_name.setText(shared.get("name", "Imported Voice"))

    def _apply_voice_filters(self, scope: str) -> None:
        source = self.my_voices if scope == "my" else self.cloned_voices
        previous_ids = {voice.get("voice_id", "") for voice in self._selected_workspace_voices(scope)}
        search = getattr(self, f"{scope}_search").text().strip()
        language = getattr(self, f"{scope}_language").currentData()
        accent = getattr(self, f"{scope}_accent").currentData()
        gender = getattr(self, f"{scope}_gender").currentData()
        age = getattr(self, f"{scope}_age").currentData()
        use_case = getattr(self, f"{scope}_use_case").currentData()

        filtered = []
        for voice in source:
            if not _voice_matches_text(voice, search):
                continue
            if language and _voice_language(voice) != language:
                continue
            if accent and _voice_label(voice, "accent") != accent:
                continue
            if gender and _voice_label(voice, "gender") != gender:
                continue
            if age and _voice_label(voice, "age") != age:
                continue
            if use_case and _voice_label(voice, "use_case") != use_case:
                continue
            filtered.append(voice)

        setattr(self, f"filtered_{scope}_voices", filtered)
        if scope == "my":
            self.my_summary_card.set_content(str(len(filtered)), "Visible after current filters")
        else:
            self.cloned_summary_card.set_content(str(len(filtered)), "Visible after current filters")
        list_widget: AccessibleListWidget = self.voice_list if scope == "my" else self.cloned_list
        selected_rows = [index for index, voice in enumerate(filtered) if voice.get("voice_id", "") in previous_ids]
        list_widget.set_items([self._workspace_item_text(voice) for voice in filtered], selected_rows=selected_rows)
        if not filtered:
            self.set_selected_voice(None, scope=scope)

    def _populate_voice_filter_options(self, scope: str, voices: list[dict]) -> None:
        options = {
            "language": OrderedDict(((_voice_language(voice), _voice_language(voice)) for voice in voices if _voice_language(voice))),
            "accent": OrderedDict(((_voice_label(voice, "accent"), _voice_label(voice, "accent")) for voice in voices if _voice_label(voice, "accent"))),
            "gender": OrderedDict(((_voice_label(voice, "gender"), _voice_label(voice, "gender")) for voice in voices if _voice_label(voice, "gender"))),
            "age": OrderedDict(((_voice_label(voice, "age"), _voice_label(voice, "age")) for voice in voices if _voice_label(voice, "age"))),
            "use_case": OrderedDict(((_voice_label(voice, "use_case"), _voice_label(voice, "use_case")) for voice in voices if _voice_label(voice, "use_case"))),
        }
        for key, values in options.items():
            combo: QComboBox = getattr(self, f"{scope}_{key}")
            current = combo.currentData()
            combo.blockSignals(True)
            label = combo.itemText(0) if combo.count() else f"All {key}"
            combo.clear()
            combo.addItem(label, "")
            for value in values.values():
                combo.addItem(value, value)
            index = combo.findData(current)
            if index >= 0:
                combo.setCurrentIndex(index)
            combo.blockSignals(False)

    def _workspace_item_text(self, voice: dict) -> str:
        parts = [
            voice.get("name", "Unknown"),
            f"type: {voice.get('category', 'n/a')}",
            f"language: {_voice_language(voice) or 'n/a'}",
        ]
        accent = _voice_label(voice, "accent")
        gender = _voice_label(voice, "gender")
        if accent:
            parts.append(f"accent: {accent}")
        if gender:
            parts.append(f"gender: {gender}")
        description = (voice.get("description") or "").strip()
        if description:
            parts.append(description[:120])
        return " | ".join(parts)

    def _shared_item_text(self, voice: dict) -> str:
        parts = [
            voice.get("name", "Unknown"),
            f"category: {voice.get('category', 'n/a')}",
            f"language: {voice.get('language', 'n/a')}",
            f"accent: {voice.get('accent', 'n/a')}",
            f"gender: {voice.get('gender', 'n/a')}",
        ]
        return " | ".join(parts)

    def _selected_workspace_voices(self, scope: str) -> list[dict]:
        data = self.filtered_my_voices if scope == "my" else self.filtered_cloned_voices
        list_widget = self.voice_list if scope == "my" else self.cloned_list
        return [data[row] for row in list_widget.selected_rows() if 0 <= row < len(data)]

    def _primary_workspace_voice(self, scope: str) -> dict | None:
        selected = self._selected_workspace_voices(scope)
        return selected[0] if selected else None

    def _selected_shared_voices(self) -> list[dict]:
        return [
            self.filtered_shared_voices[row]
            for row in self.library_list.selected_rows()
            if 0 <= row < len(self.filtered_shared_voices)
        ]

    def _primary_shared_voice(self) -> dict | None:
        selected = self._selected_shared_voices()
        return selected[0] if selected else None

    def _show_workspace_multi_selection(self, scope: str, selected: list[dict]) -> None:
        prefix = "my" if scope == "my" else "cloned"
        selected_label = getattr(self, f"{prefix}_selected_voice_label")
        name = getattr(self, f"{prefix}_voice_name")
        description = getattr(self, f"{prefix}_voice_description")
        labels = getattr(self, f"{prefix}_voice_labels")
        feedback = getattr(self, f"{prefix}_feedback")
        first = selected[0]
        selected_label.setText(
            f"{len(selected)} voices selected. First: {first.get('name', 'Unknown')} | "
            f"type: {first.get('category', 'n/a')} | language: {_voice_language(first) or 'n/a'}."
        )
        name.clear()
        description.clear()
        labels.clear()
        feedback.setText(
            "Metadata editing requires a single selected voice. Preview and Use act on the first selected voice. "
            "Delete removes all selected voices."
        )
        self._set_workspace_actions_for_selection(scope, selected)

    def _set_workspace_actions_for_selection(self, scope: str, selected: list[dict]) -> None:
        prefix = "my" if scope == "my" else "cloned"
        first = selected[0] if selected else None
        has_single = len(selected) == 1
        getattr(self, f"{prefix}_preview_button").setEnabled(bool(first and first.get("preview_url")))
        getattr(self, f"{prefix}_use_voice_button").setEnabled(bool(first))
        getattr(self, f"{prefix}_save_meta_button").setEnabled(has_single)
        getattr(self, f"{prefix}_delete_button").setEnabled(bool(first))
        getattr(self, f"{prefix}_voice_name").setEnabled(has_single)
        getattr(self, f"{prefix}_voice_description").setEnabled(has_single)
        getattr(self, f"{prefix}_voice_labels").setEnabled(has_single)

    def _set_library_actions_for_selection(self, selected: list[dict]) -> None:
        first = selected[0] if selected else None
        single = len(selected) == 1
        self.library_preview_button.setEnabled(bool(first and first.get("preview_url")))
        self.add_shared_button.setEnabled(bool(first))
        self.new_shared_name.setEnabled(single)
        if not single:
            self.new_shared_name.clear()
