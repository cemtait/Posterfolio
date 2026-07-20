from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from poster_montage_designer.version import APP_VERSION


def _alpha_bounding_rect(pixmap: QPixmap) -> QRect:
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    min_x, min_y = image.width(), image.height()
    max_x = max_y = -1
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 0:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if max_x < min_x or max_y < min_y:
        return QRect()
    return QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)


class AboutCard(QFrame):
    user_guide_requested = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        show_quick_start: bool = True,
        show_close: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("aboutCard")
        self.setFixedSize(610, 430 if show_quick_start else 360)

        icon_label = QLabel(self)
        icon_path = Path(__file__).resolve().parents[1] / "assets" / "icons" / "posterfolio_about.png"
        pixmap = QPixmap(str(icon_path))
        if not pixmap.isNull():
            crop_rect = _alpha_bounding_rect(pixmap)
            if crop_rect.isValid():
                pixmap = pixmap.copy(crop_rect)
            pixmap = pixmap.scaled(
                190,
                190,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        icon_label.setFixedWidth(215)
        icon_label.setStyleSheet("background: transparent; border: none;")

        title = QLabel("Posterfolio", self)
        title.setObjectName("aboutTitle")
        version = QLabel(f"Version {APP_VERSION}", self)
        version.setObjectName("aboutVersion")
        description = QLabel("Create beautiful film credit montages from IMDb in minutes.", self)
        description.setWordWrap(True)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(7)
        text_layout.addWidget(title)
        text_layout.addWidget(version)
        text_layout.addWidget(description)

        if show_quick_start:
            quick_heading = QLabel("Quick Start", self)
            quick_heading.setObjectName("quickStartTitle")
            quick = QLabel(
                "1. Add your TMDb API Read Access Token\n"
                "2. Import your IMDb filmography\n"
                "3. Shuffle, customise and export",
                self,
            )
            quick.setObjectName("quickStartText")
            quick.setWordWrap(True)
            text_layout.addSpacing(10)
            text_layout.addWidget(quick_heading)
            text_layout.addWidget(quick)

        guide_button = QPushButton("Open User Guide", self)
        guide_button.setObjectName("openUserGuideButton")
        guide_button.clicked.connect(self.user_guide_requested.emit)
        text_layout.addSpacing(8)
        text_layout.addWidget(guide_button)

        credits = QLabel(
            "Designed and written by Charles Tait\n"
            "Built with Python & Qt · Poster images provided by TMDb.",
            self,
        )
        credits.setObjectName("aboutCredits")
        credits.setWordWrap(True)
        text_layout.addStretch(1)
        text_layout.addWidget(credits)

        if show_close:
            close_button = QPushButton("Close", self)
            close_button.clicked.connect(self.window().close)
            text_layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(22)
        layout.addWidget(icon_label)
        layout.addLayout(text_layout, 1)


class AboutOverlay(QWidget):
    faded_out = Signal()
    user_guide_requested = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("aboutOverlay")
        self.card = AboutCard(self, show_quick_start=True)
        self.card.user_guide_requested.connect(self.user_guide_requested.emit)
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
        self._animation: QPropertyAnimation | None = None
        self.show()

    def reposition(self) -> None:
        self.setGeometry(self.parentWidget().rect())
        self.card.move((self.width() - self.card.width()) // 2, (self.height() - self.card.height()) // 2)
        self.raise_()

    def show_immediately(self) -> None:
        if self._animation is not None:
            self._animation.stop()
        self.opacity_effect.setOpacity(1.0)
        self.show()
        self.reposition()

    def fade_out(self, duration_ms: int = 1000) -> None:
        if not self.isVisible():
            return
        self._animation = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self._animation.setDuration(duration_ms)
        self._animation.setStartValue(self.opacity_effect.opacity())
        self._animation.setEndValue(0.0)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.finished.connect(self._finish_fade)
        self._animation.start()

    def _finish_fade(self) -> None:
        self.hide()
        self.faded_out.emit()


class AboutDialog(QDialog):
    user_guide_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About Posterfolio")
        self.setModal(True)
        card = AboutCard(self, show_quick_start=False, show_close=True)
        card.user_guide_requested.connect(self.user_guide_requested.emit)
        self.setFixedSize(card.width() + 28, card.height() + 28)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.addWidget(card)
