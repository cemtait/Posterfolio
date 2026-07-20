from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QDialog,
    QCheckBox,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from poster_montage_designer.config import AppConfig, load_config, save_config


class SettingsDialog(QDialog):
    """Application-wide preferences that remain useful between projects."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Posterfolio Settings")
        self.setMinimumWidth(520)

        config = load_config()

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.tmdb_token_edit = QLineEdit(self)
        self.tmdb_token_edit.setText(config.tmdb_read_token)
        self.tmdb_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.tmdb_token_edit.setPlaceholderText("TMDb API Read Access Token")
        form.addRow("TMDb read token", self.tmdb_token_edit)

        self.confirm_delete_checkbox = QCheckBox("Confirm before deleting posters", self)
        self.confirm_delete_checkbox.setChecked(
            QSettings("Posterfolio", "Posterfolio").value("confirm_delete", True, type=bool)
        )
        form.addRow("General", self.confirm_delete_checkbox)

        note = QLabel(
            "Posterfolio remembers your last project and export folders, window size, "
            "panel widths, and export format automatically.",
            self,
        )
        note.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save,
            self,
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(note)
        layout.addStretch(1)
        layout.addWidget(buttons)

    def _save(self) -> None:
        save_config(AppConfig(tmdb_read_token=self.tmdb_token_edit.text().strip()))
        QSettings("Posterfolio", "Posterfolio").setValue("confirm_delete", self.confirm_delete_checkbox.isChecked())
        self.accept()
