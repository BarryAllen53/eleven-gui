from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from eleven_gui.accessibility import defer_tab_order_chain
from eleven_gui.ui.widgets import AccessibleListWidget, HeroBanner, MetricCard, SectionCard
from eleven_gui.utils import format_count, format_percent, format_unix


class DashboardPage(QWidget):
    refresh_requested = Signal()
    settings_requested = Signal()

    def __init__(self, assets_dir) -> None:
        super().__init__()
        self.setAccessibleName("Overview page")
        self.setAccessibleDescription("Shows subscription usage, model readiness, and recent activity.")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        self.hero = HeroBanner(
            kicker="Workspace Pulse",
            title="A cleaner control surface for your ElevenLabs workspace.",
            body="Track credits, cloning access, model readiness and workspace capacity without digging through dense panels.",
            asset_path=assets_dir / "hero_orb.svg",
        )
        self.hero.primary_button.setText("Refresh All")
        self.hero.secondary_button.setText("API Settings")
        self.hero.primary_button.setAccessibleName("Refresh all workspace data")
        self.hero.secondary_button.setAccessibleName("Open API settings")
        self.hero.primary_button.clicked.connect(self.refresh_requested.emit)
        self.hero.secondary_button.clicked.connect(self.settings_requested.emit)
        self.initial_focus_widget = self.hero.primary_button

        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(14)
        self.plan_card = MetricCard("Plan")
        self.credit_card = MetricCard("Characters")
        self.voice_card = MetricCard("Voice Slots")
        self.media_card = MetricCard("Media Tools")
        metrics_layout.addWidget(self.plan_card, 0, 0)
        metrics_layout.addWidget(self.credit_card, 0, 1)
        metrics_layout.addWidget(self.voice_card, 1, 0)
        metrics_layout.addWidget(self.media_card, 1, 1)

        lower_row = QHBoxLayout()
        lower_row.setSpacing(14)

        self.credit_card_detail = SectionCard()
        credit_layout = QVBoxLayout(self.credit_card_detail)
        credit_layout.setContentsMargins(18, 18, 18, 18)
        credit_layout.setSpacing(10)
        credit_title = QLabel("Usage Detail")
        credit_title.setProperty("role", "section-title")
        self.credit_progress = QProgressBar()
        self.credit_progress.setMaximum(100)
        self.credit_progress.setValue(0)
        self.credit_progress.setFocusPolicy(Qt.StrongFocus)
        self.credit_progress.setAccessibleName("Character usage")
        self.credit_caption = QLabel("No subscription data yet.")
        self.credit_caption.setProperty("role", "muted")
        self.reset_caption = QLabel("Next reset unknown.")
        self.reset_caption.setProperty("role", "muted")
        credit_layout.addWidget(credit_title)
        credit_layout.addWidget(self.credit_progress)
        credit_layout.addWidget(self.credit_caption)
        credit_layout.addWidget(self.reset_caption)

        self.model_card = SectionCard()
        model_layout = QVBoxLayout(self.model_card)
        model_layout.setContentsMargins(18, 18, 18, 18)
        model_layout.setSpacing(10)
        model_title = QLabel("Model Readiness")
        model_title.setProperty("role", "section-title")
        self.model_summary = QLabel("Models are not loaded yet.")
        self.model_summary.setProperty("role", "muted")
        self.model_summary.setWordWrap(True)
        self.recent_summary = QLabel("History preview unavailable.")
        self.recent_summary.setProperty("role", "muted")
        self.recent_summary.setWordWrap(True)
        model_layout.addWidget(model_title)
        model_layout.addWidget(self.model_summary)
        model_layout.addWidget(self.recent_summary)
        model_layout.addStretch(1)

        self.workspace_snapshot = SectionCard()
        snapshot_layout = QVBoxLayout(self.workspace_snapshot)
        snapshot_layout.setContentsMargins(18, 18, 18, 18)
        snapshot_layout.setSpacing(10)
        snapshot_title = QLabel("Workspace Snapshot")
        snapshot_title.setProperty("role", "section-title")
        self.snapshot_list = AccessibleListWidget("Workspace snapshot list")
        snapshot_layout.addWidget(snapshot_title)
        snapshot_layout.addWidget(self.snapshot_list)

        self.activity_snapshot = SectionCard()
        activity_layout = QVBoxLayout(self.activity_snapshot)
        activity_layout.setContentsMargins(18, 18, 18, 18)
        activity_layout.setSpacing(10)
        activity_title = QLabel("Activity and Models")
        activity_title.setProperty("role", "section-title")
        self.activity_list = AccessibleListWidget("Activity and models list")
        activity_layout.addWidget(activity_title)
        activity_layout.addWidget(self.activity_list)

        lower_row.addWidget(self.credit_card_detail, 3)
        lower_row.addWidget(self.model_card, 2)

        layout.addWidget(self.hero)
        layout.addLayout(metrics_layout)
        layout.addWidget(self.workspace_snapshot)
        layout.addLayout(lower_row)
        layout.addWidget(self.activity_snapshot)
        layout.addStretch(1)
        defer_tab_order_chain(
            self,
            self.hero.primary_button,
            self.hero.secondary_button,
            self.snapshot_list,
            self.credit_progress,
            self.activity_list,
        )

    def update_data(
        self,
        *,
        subscription: dict | None,
        models: list[dict],
        voices: list[dict],
        history: list[dict],
    ) -> None:
        subscription = subscription or {}
        character_count = int(subscription.get("character_count") or 0)
        character_limit = int(subscription.get("character_limit") or 0)
        voice_used = int(subscription.get("voice_slots_used") or 0)
        voice_limit = int(subscription.get("voice_limit") or 0)
        current_for_progress = max(character_count, character_limit, 1)

        self.plan_card.set_content(
            subscription.get("tier", "Unknown").replace("_", " ").title(),
            f"Status: {subscription.get('status', 'unknown')}",
        )
        self.credit_card.set_content(
            f"{format_count(character_count)} / {format_count(character_limit)}",
            f"Usage: {format_percent(character_count, character_limit)}",
        )
        self.voice_card.set_content(
            f"{voice_used} / {voice_limit or 'N/A'}",
            f"Loaded voices: {len(voices)}",
        )
        self.media_card.set_content(
            "Dubbing + Studio",
            "Advanced media workflows may require additional plan access.",
        )

        self.credit_progress.setMaximum(current_for_progress)
        self.credit_progress.setValue(character_count)
        self.credit_caption.setText(
            f"{format_count(character_count)} characters used over a {format_count(character_limit)} cap."
        )
        self.reset_caption.setText(
            f"Next reset: {format_unix(subscription.get('next_character_count_reset_unix'))}"
        )
        self.credit_progress.setAccessibleDescription(
            f"{format_count(character_count)} characters used over a {format_count(character_limit)} cap. "
            f"Next reset: {format_unix(subscription.get('next_character_count_reset_unix'))}."
        )

        tts_models = [model for model in models if model.get("can_do_text_to_speech")]
        sts_models = [model for model in models if model.get("can_do_voice_conversion")]
        self.model_summary.setText(
            f"{len(models)} model loaded. TTS-ready: {len(tts_models)}. STS-ready: {len(sts_models)}."
        )
        if history:
            latest = history[0]
            self.recent_summary.setText(
                f"Latest activity: {latest.get('source', 'unknown')} with {latest.get('voice_name', 'unknown voice')}."
            )
        else:
            self.recent_summary.setText("History feed currently empty.")

        snapshot_items = [
            f"Plan: {subscription.get('tier', 'Unknown').replace('_', ' ').title()}",
            f"Subscription status: {subscription.get('status', 'unknown')}",
            f"Characters used: {format_count(character_count)} of {format_count(character_limit)}",
            f"Character usage percentage: {format_percent(character_count, character_limit)}",
            f"Voice slots used: {voice_used} of {voice_limit or 'N/A'}",
            f"Loaded voices: {len(voices)}",
            "Media workflows: dubbing and studio project support depends on plan and workspace permissions.",
            f"Next character reset: {format_unix(subscription.get('next_character_count_reset_unix'))}",
        ]
        self.snapshot_list.set_items(snapshot_items)

        activity_items = [
            f"Loaded models: {len(models)}",
            f"Text to speech capable models: {len(tts_models)}",
            f"Speech to speech capable models: {len(sts_models)}",
            f"History items loaded: {len(history)}",
        ]
        if history:
            latest = history[0]
            activity_items.extend(
                [
                    f"Latest history source: {latest.get('source', 'unknown')}",
                    f"Latest history voice: {latest.get('voice_name', 'unknown voice')}",
                    f"Latest history model: {latest.get('model_id', 'unknown model')}",
                    f"Latest history state: {latest.get('state', 'unknown')}",
                ]
            )
        else:
            activity_items.append("History feed is currently empty.")
        self.activity_list.set_items(activity_items)
