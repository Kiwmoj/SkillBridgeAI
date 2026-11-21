from collections.abc import Callable
from dataclasses import dataclass

from PyQt6.QtWidgets import QCheckBox, QLabel, QMessageBox, QPushButton, QVBoxLayout

from apps.desktop.ui.components.widgets import add_action, text_label
from apps.desktop.ui.pages.base import Page, PageContext


@dataclass(frozen=True)
class AccountActions:
    sign_out: Callable[[], None]
    recovery_code: Callable[[], None]
    delete_account: Callable[[], None]


class SettingsPage(Page):
    title = "Settings"

    def __init__(self, context: PageContext, account: AccountActions | None = None) -> None:
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h1>Settings</h1>"))
        layout.addWidget(text_label(f"Connected backend: {self.backend.base_url}. To change it, sign out first."))
        if account is not None:
            add_action(layout, "Sign out", account.sign_out)
            add_action(layout, "Generate a one-time recovery code", account.recovery_code)
            if self.session.role == "student":
                add_action(layout, "Delete my account", account.delete_account)
        layout.addWidget(
            QLabel(
                "AI provider credentials are configured only on the backend "
                "and are never exposed to this application."
            )
        )

        layout.addWidget(QLabel("<b>Training permission</b>"))
        self.training_consent = QCheckBox(
            "Allow per-contribution opt-in to future reviewed training drafts"
        )
        layout.addWidget(text_label("Turning this on does not grant permission for past submissions. Turning it off "
                                    "withdraws all contribution training permissions and revokes affected drafts."))
        layout.addWidget(self.training_consent)
        save_consent = QPushButton("Update training permission")
        layout.addWidget(save_consent)
        save_consent.clicked.connect(self.save_training_consent)
        self.run(
            self.backend.training_consent,
            lambda result: self.training_consent.setChecked(result["consent_enabled"]),
        )
        layout.addStretch()

    def save_training_consent(self) -> None:
        enabled = self.training_consent.isChecked()
        self.run(
            lambda: self.backend.update_training_consent(enabled),
            lambda _: QMessageBox.information(
                self.context.parent,
                "Training permission",
                "Your future training permission has been updated.",
            ),
        )
