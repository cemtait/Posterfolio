from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
)

from poster_montage_designer.layouts.grid import GridLayout
from poster_montage_designer.models import Project
from poster_montage_designer.services.export_resolution import calculate_max_export_width_px


FORMAT_SUFFIXES = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "TIFF": ".tif",
    "PDF": ".pdf",
}

FORMAT_FILTERS = {
    "PNG": "PNG Image (*.png)",
    "JPEG": "JPEG Image (*.jpg *.jpeg)",
    "TIFF": "TIFF Image (*.tif *.tiff)",
    "PDF": "PDF Document (*.pdf)",
}


class ExportDialog(QDialog):
    MIN_QUALITY = 10
    MAX_QUALITY = 100

    def __init__(
        self,
        *,
        project: Project,
        layout: GridLayout,
        visible_imdb_ids: list[str],
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.project = project
        self.layout = layout
        self.visible_imdb_ids = visible_imdb_ids
        self.settings = QSettings("Posterfolio", "Posterfolio")

        self.max_width_px = calculate_max_export_width_px(
            project=project,
            layout=layout,
            visible_imdb_ids=visible_imdb_ids,
        )
        self.max_width_px = max(800, int(self.max_width_px))

        self.setWindowTitle("Export Image")
        self.setMinimumWidth(440)

        layout_widget = QVBoxLayout(self)

        form = QFormLayout()
        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["PNG", "JPEG", "TIFF", "PDF"])
        last_format = str(self.settings.value("export/format", "PNG"))
        if last_format in FORMAT_SUFFIXES:
            self.format_combo.setCurrentText(last_format)
        form.addRow("Format", self.format_combo)

        self.quality_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.quality_slider.setRange(self.MIN_QUALITY, self.MAX_QUALITY)
        last_quality = int(self.settings.value("export/quality", self.MAX_QUALITY))
        self.quality_slider.setValue(max(self.MIN_QUALITY, min(self.MAX_QUALITY, last_quality)))
        form.addRow("Quality", self.quality_slider)

        self.size_label = QLabel(self)
        self.size_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("Export size", self.size_label)

        self.info_label = QLabel(self)
        self.info_label.setWordWrap(True)
        form.addRow("", self.info_label)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok,
            self,
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Export")

        layout_widget.addLayout(form)
        layout_widget.addWidget(self.button_box)

        self.format_combo.currentTextChanged.connect(self._update_labels)
        self.quality_slider.valueChanged.connect(self._update_labels)
        self.button_box.accepted.connect(self._accept)
        self.button_box.rejected.connect(self.reject)

        self._update_labels()

    def output_format(self) -> str:
        return self.format_combo.currentText().lower()

    def default_suffix(self) -> str:
        return FORMAT_SUFFIXES[self.format_combo.currentText()]

    def file_filter(self) -> str:
        current = self.format_combo.currentText()
        other_filters = [value for key, value in FORMAT_FILTERS.items() if key != current]
        return ";;".join([FORMAT_FILTERS[current], *other_filters, "All Files (*.*)"])

    def default_output_path(self) -> str:
        safe_name = _safe_filename(self.project.name or "poster_montage")
        return str(Path("exports") / f"{safe_name}{self.default_suffix()}")

    def export_width_px(self) -> int:
        quality = self.quality_slider.value() / self.MAX_QUALITY
        return max(1, round(self.max_width_px * quality))

    def export_height_px(self) -> int:
        return max(1, round(self.export_width_px() * self.project.page_height_mm / self.project.page_width_mm))

    def _accept(self) -> None:
        self.settings.setValue("export/format", self.format_combo.currentText())
        self.settings.setValue("export/quality", self.quality_slider.value())
        self.accept()

    def _update_labels(self) -> None:
        width = self.export_width_px()
        height = self.export_height_px()
        megapixels = (width * height) / 1_000_000.0
        maximum_text = "Maximum" if self.quality_slider.value() == self.MAX_QUALITY else f"{self.quality_slider.value()}% of maximum"

        self.size_label.setText(f"{width:,} × {height:,} px")

        format_name = self.format_combo.currentText()
        estimate_mb = _estimate_file_size_mb(width, height, format_name)
        message = f"{maximum_text}\n≈ {megapixels:.1f} megapixels"
        if estimate_mb is not None:
            message += f"\nEstimated {format_name}: ~{estimate_mb:.0f} MB"
        if self.quality_slider.value() == self.MAX_QUALITY:
            message += "\nNo poster should be enlarged beyond its original pixels."
        self.info_label.setText(message)


def _estimate_file_size_mb(width: int, height: int, format_name: str) -> float | None:
    pixels = width * height
    raw_rgb_mb = pixels * 3 / 1_000_000.0

    if format_name == "JPEG":
        return raw_rgb_mb * 0.18
    if format_name == "PNG":
        return raw_rgb_mb * 0.55
    if format_name == "TIFF":
        return raw_rgb_mb
    if format_name == "PDF":
        return raw_rgb_mb * 0.55
    return None


def _safe_filename(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in (" ", "-", "_") else "_" for char in value)
    cleaned = "_".join(cleaned.split())
    return cleaned or "poster_montage"
