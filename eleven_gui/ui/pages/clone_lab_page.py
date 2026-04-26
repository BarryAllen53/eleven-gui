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
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from eleven_gui.accessibility import configure_focusable_text_edit, set_tab_order_chain
from eleven_gui.ui.widgets import AccessibleListWidget, HeroBanner, MetricCard, ProgressStatusCard, SectionCard, build_icon


class CloneLabPage(QWidget):
    create_clone_requested = Signal(object)
    preview_sample_requested = Signal(str)
    stop_preview_requested = Signal()
    preview_clone_requested = Signal(str, str)
    use_clone_requested = Signal(object)
    delete_clone_requested = Signal(object)
    fetch_pvc_captcha_requested = Signal(str)
    verify_pvc_captcha_requested = Signal(object)
    train_pvc_requested = Signal(object)
    cancel_clone_requested = Signal()

    def __init__(self, assets_dir) -> None:
        super().__init__()
        self.sample_paths: list[Path] = []
        self.cloned_voices: list[dict] = []
        self._busy = False
        self._pvc_enabled = False
        self.setAccessibleName("Clone Lab page")
        self.setAccessibleDescription("Create instant or professional voice clones from sample audio.")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        self.hero = HeroBanner(
            kicker="Clone Lab",
            title="Build a clone from a calmer, step-based workspace.",
            body="Instant cloning stays fast. Professional cloning keeps verification and training separate so the flow is easier to follow.",
            asset_path=assets_dir / "clone_lab.svg",
        )
        self.hero.primary_button.setText("Add Samples")
        self.hero.secondary_button.setText("Create Clone")
        self.hero.primary_button.setAccessibleName("Add sample files")
        self.hero.secondary_button.setAccessibleName("Create clone")
        self.hero.primary_button.clicked.connect(self._pick_samples)
        self.hero.secondary_button.clicked.connect(self._emit_create_clone)
        layout.addWidget(self.hero)

        self.page_status = QLabel("Start with samples, choose the clone type, then move through create, verify and train steps.")
        self.page_status.setProperty("role", "muted")
        self.page_status.setAccessibleName("Clone Lab status")
        self.page_status.setWordWrap(True)
        layout.addWidget(self.page_status)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(14)
        self.sample_count_card = MetricCard("Samples", "0", "Audio files ready for upload")
        self.clone_mode_card = MetricCard("Clone Mode", "IVC", "Instant workflow is active")
        self.clone_count_card = MetricCard("Cloned Voices", "0", "Voices available in your workspace")
        summary_row.addWidget(self.sample_count_card)
        summary_row.addWidget(self.clone_mode_card)
        summary_row.addWidget(self.clone_count_card)
        layout.addLayout(summary_row)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        form_card = SectionCard()
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(18, 18, 18, 18)
        form_layout.setSpacing(12)
        title = QLabel("Clone Request")
        title.setProperty("role", "section-title")
        self.capability_label = QLabel("Capabilities not loaded yet.")
        self.capability_label.setProperty("role", "muted")
        self.capability_label.setWordWrap(True)
        self.clone_feedback = QLabel("Preview and create stay disabled until your sample set is ready.")
        self.clone_feedback.setProperty("role", "muted")
        self.clone_feedback.setWordWrap(True)

        form = QFormLayout()
        self.clone_type = QComboBox()
        self.clone_type.addItem("Instant Voice Clone", "ivc")
        self.clone_type.addItem("Professional Voice Clone", "pvc")
        self.clone_type.currentIndexChanged.connect(self._update_form_hints)
        self.clone_language = QLineEdit()
        self.clone_language.setPlaceholderText("en")
        self.clone_language.setAccessibleName("Clone language")
        self.clone_name = QLineEdit()
        self.clone_name.setPlaceholderText("Narrator TR")
        self.clone_name.setAccessibleName("Clone voice name")
        self.clone_name.textChanged.connect(self._update_create_state)
        self.clone_description = QTextEdit()
        self.clone_description.setFixedHeight(88)
        configure_focusable_text_edit(
            self.clone_description,
            name="Clone description",
            description="Optional notes for the clone. Press Tab to move forward.",
        )
        self.clone_labels = QLineEdit()
        self.clone_labels.setPlaceholderText("locale:tr, style:cinematic")
        self.clone_labels.setAccessibleName("Clone labels")
        self.remove_bg = QCheckBox("Remove background noise")
        self.remove_bg.setChecked(False)
        type_label = QLabel("&Clone type")
        type_label.setBuddy(self.clone_type)
        language_label = QLabel("&Language")
        language_label.setBuddy(self.clone_language)
        name_label = QLabel("&Name")
        name_label.setBuddy(self.clone_name)
        description_label = QLabel("&Description")
        description_label.setBuddy(self.clone_description)
        labels_label = QLabel("La&bels")
        labels_label.setBuddy(self.clone_labels)
        form.addRow(type_label, self.clone_type)
        form.addRow(language_label, self.clone_language)
        form.addRow(name_label, self.clone_name)
        form.addRow(description_label, self.clone_description)
        form.addRow(labels_label, self.clone_labels)

        sample_row = QHBoxLayout()
        self.pick_button = QPushButton("&Add Samples")
        self.pick_button.setIcon(build_icon("upload"))
        self.pick_button.clicked.connect(self._pick_samples)
        self.preview_sample_button = QPushButton("Preview Samp&le")
        self.preview_sample_button.setIcon(build_icon("play"))
        self.preview_sample_button.clicked.connect(self._emit_preview_sample)
        self.stop_sample_button = QPushButton("Stop Pre&view")
        self.stop_sample_button.setIcon(build_icon("stop"))
        self.stop_sample_button.clicked.connect(self.stop_preview_requested.emit)
        self.remove_samples_button = QPushButton("&Remove Selected")
        self.remove_samples_button.setProperty("variant", "danger")
        self.remove_samples_button.clicked.connect(self._remove_selected_samples)
        self.clear_button = QPushButton("C&lear All")
        self.clear_button.clicked.connect(self._clear_samples)
        sample_row.addWidget(self.pick_button)
        sample_row.addWidget(self.preview_sample_button)
        sample_row.addWidget(self.stop_sample_button)
        sample_row.addWidget(self.remove_samples_button)
        sample_row.addWidget(self.clear_button)

        self.create_button = QPushButton("Create &Clone")
        self.create_button.setProperty("variant", "primary")
        self.create_button.clicked.connect(self._emit_create_clone)

        form_layout.addWidget(title)
        form_layout.addWidget(self.capability_label)
        form_layout.addLayout(form)
        form_layout.addWidget(self.remove_bg)
        form_layout.addWidget(self.clone_feedback)
        form_layout.addLayout(sample_row)
        form_layout.addWidget(self.create_button)

        self.progress_card = ProgressStatusCard("Clone Progress")
        self.progress_card.cancel_requested.connect(self.cancel_clone_requested.emit)

        top_row.addWidget(form_card, 3)
        top_row.addWidget(self.progress_card, 2)
        layout.addLayout(top_row)

        lower_row = QHBoxLayout()
        lower_row.setSpacing(14)

        samples_card = SectionCard()
        samples_layout = QVBoxLayout(samples_card)
        samples_layout.setContentsMargins(18, 18, 18, 18)
        samples_layout.setSpacing(10)
        list_title = QLabel("Sample Files")
        list_title.setProperty("role", "section-title")
        self.file_list = AccessibleListWidget(
            "Sample files list",
            multi_select=True,
            drag_reorder=True,
            accept_file_drop=True,
        )
        self.file_list.files_dropped.connect(self._handle_dropped_files)
        self.file_list.order_changed.connect(self._sync_sample_order)
        self.file_list.itemSelectionChanged.connect(self._update_sample_preview_state)
        samples_layout.addWidget(list_title)
        samples_layout.addWidget(self.file_list)

        clones_card = SectionCard()
        clones_layout = QVBoxLayout(clones_card)
        clones_layout.setContentsMargins(18, 18, 18, 18)
        clones_layout.setSpacing(10)
        clones_title = QLabel("Cloned Voices")
        clones_title.setProperty("role", "section-title")
        self.clone_table = AccessibleListWidget("Cloned voices list", multi_select=True)
        self.clone_table.itemSelectionChanged.connect(self._update_clone_detail)
        self.clone_detail = QLabel("Your cloned voices will appear here.")
        self.clone_detail.setProperty("role", "muted")
        self.clone_detail.setWordWrap(True)

        clone_actions = QHBoxLayout()
        self.preview_clone_button = QPushButton("&Preview Clone")
        self.preview_clone_button.setIcon(build_icon("play"))
        self.preview_clone_button.clicked.connect(self._emit_preview_clone)
        self.use_clone_button = QPushButton("&Use In Studio")
        self.use_clone_button.setProperty("variant", "primary")
        self.use_clone_button.setIcon(build_icon("link"))
        self.use_clone_button.clicked.connect(self._emit_use_clone)
        self.delete_clone_button = QPushButton("&Delete Clone")
        self.delete_clone_button.setProperty("variant", "danger")
        self.delete_clone_button.setIcon(build_icon("delete"))
        self.delete_clone_button.clicked.connect(self._emit_delete_clone)
        clone_actions.addWidget(self.preview_clone_button)
        clone_actions.addWidget(self.use_clone_button)
        clone_actions.addWidget(self.delete_clone_button)
        clone_actions.addStretch(1)

        pvc_controls = QFormLayout()
        self.verification_recording = QLineEdit()
        self.verification_recording.setReadOnly(True)
        self.verification_recording.setPlaceholderText("Select the captcha reading or verification recording")
        self.pick_verification_button = QPushButton("&Browse Verification Recording")
        self.pick_verification_button.clicked.connect(self._pick_verification_recording)
        recording_row = QHBoxLayout()
        recording_row.addWidget(self.verification_recording, 1)
        recording_row.addWidget(self.pick_verification_button)
        pvc_controls.addRow(QLabel("Verification &recording"), recording_row)

        pvc_action_row = QHBoxLayout()
        self.fetch_captcha_button = QPushButton("Get &Captcha")
        self.fetch_captcha_button.clicked.connect(self._emit_fetch_captcha)
        self.verify_captcha_button = QPushButton("&Verify Owner")
        self.verify_captcha_button.clicked.connect(self._emit_verify_captcha)
        self.train_button = QPushButton("Start &Training")
        self.train_button.clicked.connect(self._emit_train)
        pvc_action_row.addWidget(self.fetch_captcha_button)
        pvc_action_row.addWidget(self.verify_captcha_button)
        pvc_action_row.addWidget(self.train_button)
        pvc_action_row.addStretch(1)

        self.captcha_status = QLabel("Professional clone verification is available only when a professional clone is selected.")
        self.captcha_status.setProperty("role", "muted")
        self.captcha_status.setWordWrap(True)

        clones_layout.addWidget(clones_title)
        clones_layout.addWidget(self.clone_table, 1)
        clones_layout.addWidget(self.clone_detail)
        clones_layout.addLayout(clone_actions)
        clones_layout.addLayout(pvc_controls)
        clones_layout.addLayout(pvc_action_row)
        clones_layout.addWidget(self.captcha_status)

        lower_row.addWidget(samples_card, 2)
        lower_row.addWidget(clones_card, 3)
        layout.addLayout(lower_row, 1)
        self.initial_focus_widget = self.clone_type
        set_tab_order_chain(
            self.hero.primary_button,
            self.hero.secondary_button,
            self.clone_type,
            self.clone_language,
            self.clone_name,
            self.clone_description,
            self.clone_labels,
            self.remove_bg,
            self.pick_button,
            self.preview_sample_button,
            self.stop_sample_button,
            self.remove_samples_button,
            self.clear_button,
            self.create_button,
            self.progress_card.cancel_button,
            self.file_list,
            self.clone_table,
            self.preview_clone_button,
            self.use_clone_button,
            self.delete_clone_button,
            self.verification_recording,
            self.pick_verification_button,
            self.fetch_captcha_button,
            self.verify_captcha_button,
            self.train_button,
        )
        self._update_form_hints()
        self._update_sample_preview_state()
        self._update_create_state()
        self._update_clone_actions(False)

    def set_subscription(self, subscription: dict | None) -> None:
        subscription = subscription or {}
        ivc = "enabled" if subscription.get("can_use_instant_voice_cloning") else "disabled"
        pvc = "enabled" if subscription.get("can_use_professional_voice_cloning") else "disabled"
        self._pvc_enabled = bool(subscription.get("can_use_professional_voice_cloning"))
        self.clone_type.model().item(1).setEnabled(self._pvc_enabled)
        if not self._pvc_enabled and self.clone_type.currentData() == "pvc":
            self.clone_type.setCurrentIndex(0)
        self.capability_label.setText(
            f"Instant Voice Cloning: {ivc}. Professional Voice Cloning: {pvc}. "
            f"Voice slots used: {subscription.get('voice_slots_used', 0)} / {subscription.get('voice_limit', 0)}. "
            f"Professional slots used: {subscription.get('professional_voice_slots_used', 0)} / {subscription.get('professional_voice_limit', 0)}."
        )
        self._update_form_hints()

    def set_cloned_voices(self, voices: list[dict]) -> None:
        self.cloned_voices = [
            voice for voice in voices if (voice.get("category") or "").lower() in {"cloned", "professional"}
        ]
        self.clone_count_card.set_content(str(len(self.cloned_voices)), "Voices available in your workspace")
        rows = []
        for voice in self.cloned_voices:
            training = self._training_summary(voice)
            rows.append(
                " | ".join(
                    [
                        voice.get("name", "Unknown"),
                        f"type: {voice.get('category', 'n/a')}",
                        f"language: {(voice.get('fine_tuning') or {}).get('language') or '-'}",
                        f"training: {training}",
                        f"preview: {'yes' if voice.get('preview_url') else 'no'}",
                    ]
                )
            )
        self.clone_table.set_items(rows)
        self._update_clone_detail()

    def show_status(self, text: str) -> None:
        self.page_status.setText(text)
        self.clone_feedback.setText(text)

    def set_progress(self, percent: int, status: str, detail: str, *, busy: bool) -> None:
        self.progress_card.set_state(percent, status, detail, running=busy)
        self.page_status.setText(status)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        controls = (
            self.hero.primary_button,
            self.hero.secondary_button,
            self.clone_type,
            self.clone_language,
            self.clone_name,
            self.clone_description,
            self.clone_labels,
            self.remove_bg,
            self.pick_button,
            self.preview_sample_button,
            self.stop_sample_button,
            self.remove_samples_button,
            self.clear_button,
            self.file_list,
            self.clone_table,
            self.preview_clone_button,
            self.use_clone_button,
            self.delete_clone_button,
            self.fetch_captcha_button,
            self.verify_captcha_button,
            self.train_button,
            self.pick_verification_button,
        )
        for widget in controls:
            widget.setEnabled(not busy)
        self.progress_card.cancel_button.setVisible(busy)
        self._update_create_state()
        self._update_clone_detail()

    def set_captcha_status(self, text: str) -> None:
        self.captcha_status.setText(text)

    def _pick_samples(self) -> None:
        if self._busy:
            return
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select voice samples",
            "",
            "Audio Files (*.mp3 *.wav *.m4a *.flac *.ogg)",
        )
        if not files:
            return
        added = self._add_sample_paths([Path(file_name) for file_name in files])
        if added:
            self.show_status(f"{len(self.sample_paths)} sample file(s) ready.")

    def _pick_verification_recording(self) -> None:
        if self._busy:
            return
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select verification recording",
            "",
            "Audio Files (*.mp3 *.wav *.m4a *.flac *.ogg)",
        )
        if file_name:
            self.verification_recording.setText(file_name)
            self._update_clone_detail()

    def _clear_samples(self) -> None:
        if self._busy:
            return
        self.sample_paths = []
        self._refresh_list()
        self.show_status("Sample set cleared.")

    def _refresh_list(self) -> None:
        selected_paths = {str(path) for path in self._selected_sample_paths()}
        self.file_list.clear()
        for path in self.sample_paths:
            item = QListWidgetItem(f"{path.name}  |  {path.parent}")
            item.setToolTip(str(path))
            item.setData(Qt.UserRole, str(path))
            self.file_list.addItem(item)
        restored_rows = [index for index, path in enumerate(self.sample_paths) if str(path) in selected_paths]
        if restored_rows:
            for row in restored_rows:
                current_item = self.file_list.item(row)
                if current_item is not None:
                    current_item.setSelected(True)
            self.file_list.setCurrentRow(restored_rows[0])
        elif self.sample_paths:
            self.file_list.setCurrentRow(0)
        self._update_sample_preview_state()
        self._update_create_state()
        self.sample_count_card.set_content(str(len(self.sample_paths)), "Audio files ready for upload")

    def _emit_preview_sample(self) -> None:
        path = self._current_sample_path()
        if path is not None:
            self.preview_sample_requested.emit(str(path))

    def _emit_create_clone(self) -> None:
        if self._busy:
            return
        self.create_clone_requested.emit(
            {
                "clone_type": self.clone_type.currentData(),
                "language": self.clone_language.text().strip() or "en",
                "name": self.clone_name.text().strip(),
                "description": self.clone_description.toPlainText().strip(),
                "labels_text": self.clone_labels.text().strip(),
                "remove_background_noise": self.remove_bg.isChecked(),
                "sample_paths": [str(path) for path in self.sample_paths],
            }
        )

    def _emit_preview_clone(self) -> None:
        clone = self._current_clone()
        if clone and clone.get("preview_url"):
            self.preview_clone_requested.emit(clone.get("name", "Clone Preview"), clone.get("preview_url", ""))

    def _emit_use_clone(self) -> None:
        clone = self._current_clone()
        if clone:
            self.use_clone_requested.emit(clone)

    def _emit_delete_clone(self) -> None:
        selected = self._selected_clones()
        if selected:
            self.delete_clone_requested.emit([clone.get("voice_id", "") for clone in selected if clone.get("voice_id")])

    def _emit_fetch_captcha(self) -> None:
        clone = self._current_clone()
        if clone:
            self.fetch_pvc_captcha_requested.emit(clone.get("voice_id", ""))

    def _emit_verify_captcha(self) -> None:
        clone = self._current_clone()
        if clone and self.verification_recording.text().strip():
            self.verify_pvc_captcha_requested.emit(
                {
                    "voice_id": clone.get("voice_id", ""),
                    "recording_path": self.verification_recording.text().strip(),
                }
            )

    def _emit_train(self) -> None:
        clone = self._current_clone()
        if clone:
            self.train_pvc_requested.emit(
                {
                    "voice_id": clone.get("voice_id", ""),
                    "model_id": "eleven_multilingual_v2",
                }
            )

    def _current_sample_path(self) -> Path | None:
        rows = self.file_list.selected_rows()
        if not rows:
            return None
        row = rows[0]
        return self.sample_paths[row] if 0 <= row < len(self.sample_paths) else None

    def _current_clone(self) -> dict | None:
        selected = self._selected_clones()
        return selected[0] if selected else None

    def _selected_sample_paths(self) -> list[Path]:
        return [self.sample_paths[row] for row in self.file_list.selected_rows() if 0 <= row < len(self.sample_paths)]

    def _selected_clones(self) -> list[dict]:
        return [self.cloned_voices[row] for row in self.clone_table.selected_rows() if 0 <= row < len(self.cloned_voices)]

    def _update_sample_preview_state(self) -> None:
        has_sample = bool(self._selected_sample_paths())
        self.preview_sample_button.setEnabled(has_sample and not self._busy)
        self.stop_sample_button.setEnabled(has_sample and not self._busy)
        self.remove_samples_button.setEnabled(has_sample and not self._busy)
        self.clear_button.setEnabled(bool(self.sample_paths) and not self._busy)

    def _update_create_state(self) -> None:
        wants_pvc = self.clone_type.currentData() == "pvc"
        has_minimum = bool(self.clone_name.text().strip() and self.sample_paths)
        language_ok = bool(self.clone_language.text().strip() or not wants_pvc)
        enabled = has_minimum and language_ok and not self._busy
        self.create_button.setEnabled(enabled)
        self.hero.secondary_button.setEnabled(enabled)

    def _update_form_hints(self) -> None:
        if self.clone_type.currentData() == "pvc":
            text = (
                "Professional clone selected. Samples are uploaded first, then owner verification and training continue "
                "through the controls below."
            )
            self.clone_mode_card.set_content("PVC", "Verification and training remain visible")
        else:
            text = "Instant clone selected. Once samples and a name are ready, Create Clone will generate the voice directly."
            self.clone_mode_card.set_content("IVC", "Fast creation with the current sample set")
        if not self._pvc_enabled and self.clone_type.currentData() == "pvc":
            text = "Professional voice cloning is not available on this account."
        self.clone_feedback.setText(text)
        self._update_create_state()

    def _update_clone_detail(self) -> None:
        selected = self._selected_clones()
        clone = selected[0] if selected else None
        if not clone:
            self.clone_detail.setText("Select a cloned voice to preview it, use it in Studio, or continue PVC steps.")
            self.captcha_status.setText(
                "Professional clone verification is available only when a professional clone is selected."
            )
            self._update_clone_actions(False)
            return
        if len(selected) > 1:
            professional_count = sum(1 for item in selected if (item.get("category") or "").lower() == "professional")
            self.clone_detail.setText(
                f"{len(selected)} cloned voices selected. Preview and Use act on the first selected clone. "
                "Delete removes all selected clones."
            )
            self.captcha_status.setText(
                "Verification and training require a single selected professional clone. "
                f"Professional clones in selection: {professional_count}."
            )
            self._update_clone_actions(True)
            return

        fine_tuning = clone.get("fine_tuning") or {}
        verification_count = fine_tuning.get("verification_attempts_count", 0)
        self.clone_detail.setText(
            f"{clone.get('name', 'Unknown')} | type: {clone.get('category', 'n/a')} | "
            f"training: {self._training_summary(clone)} | verification attempts: {verification_count}."
        )
        is_professional = (clone.get("category") or "").lower() == "professional"
        if is_professional:
            self.captcha_status.setText(
                "Professional clone selected. Use Get Captcha, then choose the spoken recording and verify before training."
            )
        else:
            self.captcha_status.setText("Instant clones do not require captcha verification or training.")
        self._update_clone_actions(True)

    def _update_clone_actions(self, has_selection: bool) -> None:
        selected = self._selected_clones() if has_selection else []
        clone = selected[0] if selected else None
        single_selected = len(selected) == 1
        is_professional = bool(single_selected and clone and (clone.get("category") or "").lower() == "professional")
        has_recording = bool(self.verification_recording.text().strip())
        self.preview_clone_button.setEnabled(bool(clone and clone.get("preview_url")) and not self._busy)
        self.use_clone_button.setEnabled(bool(clone) and not self._busy)
        self.delete_clone_button.setEnabled(bool(clone) and not self._busy)
        self.pick_verification_button.setEnabled(is_professional and not self._busy)
        self.fetch_captcha_button.setEnabled(is_professional and not self._busy)
        self.verify_captcha_button.setEnabled(is_professional and has_recording and not self._busy)
        self.train_button.setEnabled(is_professional and not self._busy)

    def _remove_selected_samples(self) -> None:
        if self._busy:
            return
        selected = self._selected_sample_paths()
        if not selected:
            return
        selected_set = set(selected)
        self.sample_paths = [path for path in self.sample_paths if path not in selected_set]
        self._refresh_list()
        self.show_status(f"Removed {len(selected)} sample file(s).")

    def _handle_dropped_files(self, file_paths: list[str]) -> None:
        if self._busy:
            return
        added = self._add_sample_paths([Path(path) for path in file_paths])
        if added:
            self.show_status(f"Added {added} sample file(s) from drag and drop.")

    def _sync_sample_order(self, ordered_paths: list[object]) -> None:
        if not ordered_paths:
            return
        order = [Path(value) for value in ordered_paths if isinstance(value, str) and value]
        if len(order) != len(self.sample_paths):
            return
        self.sample_paths = order
        self._update_sample_preview_state()

    def _add_sample_paths(self, paths: list[Path]) -> int:
        added = 0
        allowed = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
        for path in paths:
            if path.suffix.lower() not in allowed or path in self.sample_paths:
                continue
            self.sample_paths.append(path)
            added += 1
        if added:
            self._refresh_list()
        else:
            self._update_sample_preview_state()
        return added

    def _training_summary(self, voice: dict) -> str:
        fine_tuning = voice.get("fine_tuning") or {}
        states = fine_tuning.get("state") or {}
        if isinstance(states, dict) and states:
            return ", ".join(f"{model}:{state}" for model, state in states.items())
        if fine_tuning.get("is_allowed_to_fine_tune"):
            return "ready"
        return "n/a"
