import sys

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from poster_montage_designer.windows.main_window import MainWindow


DARK_THEME = """
QMainWindow { background-color: #2b2b2b; }

QWidget {
    background-color: #2b2b2b;
    color: #d6d6d6;
    font-family: Segoe UI;
    font-size: 10pt;
}

QLabel { color: #d6d6d6; }

QLabel#projectTitleLabel,
QLabel#propertiesTitleLabel {
    font-size: 12pt;
    font-weight: 600;
    color: #f0f0f0;
}

QLabel#titleListTitleLabel,
QLabel#benchListTitleLabel {
    margin-top: 8px;
    font-weight: 600;
    color: #f0f0f0;
}


QFrame#aboutCard {
    background-color: #1d2227;
    border: 1px solid #59636c;
    border-radius: 14px;
}
QLabel#aboutTitle { font-size: 24pt; font-weight: 600; color: #f2f2f2; }
QLabel#aboutVersion { font-size: 12pt; color: #57a9e8; }

QLabel#projectSummaryLabel {
    background-color: #232323;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 5px 7px;
    color: #cfcfcf;
    font-size: 9pt;
}

QLabel#posterPreviewLabel {
    background-color: transparent;
    border: none;
    padding: 0;
}

QPushButton {
    background-color: #3a3a3a;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 6px 12px;
}

QPushButton:hover { background-color: #444444; }
QComboBox {
    background-color: #3a3a3a;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px 28px 5px 9px;
}
QComboBox:hover { background-color: #444444; }
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #2b2b2b;
    color: #d6d6d6;
    border: 1px solid #555555;
    selection-background-color: #4a637a;
}

QPushButton:pressed { background-color: #2f2f2f; }
QPushButton:disabled {
    background-color: #303030;
    color: #777777;
    border-color: #3d3d3d;
}

QSplitter#mainSplitter::handle { background-color: #1f1f1f; }
QSplitter#mainSplitter::handle:horizontal { width: 5px; }
QSplitter#mainSplitter::handle:hover { background-color: #4a637a; }

QListWidget {
    background-color: #111111;
    border: 1px solid #5a5a5a;
    border-radius: 5px;
    padding: 3px;
    outline: none;
}

QListWidget::viewport { background-color: #111111; }

QListWidget::item {
    padding: 1px 6px;
    min-height: 15px;
    border-left: 4px solid transparent;
}

QListWidget::item:hover { background-color: #2a3036; }

QListWidget::item:selected,
QListWidget::item:selected:active,
QListWidget::item:selected:!active {
    background-color: #2d6fa3;
    color: #ffffff;
    border-left: 4px solid #b7ddff;
}

QLabel#progressLabel {
    color: #c8c8c8;
    font-size: 9pt;
}

QLabel#progressLabel[active="false"] { color: transparent; }

QProgressBar#projectProgressBar {
    background-color: #1f1f1f;
    border: 1px solid #444444;
    border-radius: 5px;
    min-height: 18px;
    max-height: 18px;
    text-align: center;
    color: transparent;
}

QProgressBar#projectProgressBar::chunk {
    background-color: #4f7899;
    border-radius: 4px;
}

QProgressBar#projectProgressBar[active="false"] {
    background-color: transparent;
    border-color: transparent;
}

QProgressBar#projectProgressBar[active="false"]::chunk { background-color: transparent; }

QSlider::groove:horizontal {
    height: 5px;
    background: #222222;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #6f91ad;
    border: 1px solid #9bbbd5;
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover { background: #83a8c7; }

QScrollBar:vertical {
    background-color: #242424;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #555555;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover { background-color: #666666; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
    border: none;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical { background: none; }

QScrollBar:horizontal {
    background-color: #242424;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #555555;
    border-radius: 5px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover { background-color: #666666; }
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
    background: none;
    border: none;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal { background: none; }

QMenuBar {
    background-color: #262626;
    color: #d6d6d6;
}
QMenuBar::item:selected { background-color: #3a3a3a; }
QMenu {
    background-color: #2b2b2b;
    color: #d6d6d6;
    border: 1px solid #444444;
}
QMenu::item:selected { background-color: #4a637a; }

QFrame#progressPopup {
    background-color: rgba(35, 35, 35, 235);
    border: 1px solid #555555;
    border-radius: 8px;
}

QListWidget#benchPosterList {
    background-color: #161616;
    border: 1px solid #444444;
    border-radius: 5px;
    padding: 6px;
}
QListWidget#benchPosterList::item {
    background: transparent;
    border: none;
    padding: 2px;
    margin: 0;
}
QListWidget#benchPosterList::item:hover {
    background: transparent;
    border: none;
}
QListWidget#benchPosterList::item:selected,
QListWidget#benchPosterList::item:selected:active,
QListWidget#benchPosterList::item:selected:!active {
    background-color: transparent;
    border: none;
    border-left: none;
    border-right: none;
    border-top: none;
    border-bottom: none;
}


QFrame#aboutCard QLabel { background: transparent; }
QFrame#aboutCard {
    background-color: #242424;
    border: 1px solid #5b7183;
    border-radius: 14px;
}
QLabel#aboutTitle {
    font-size: 22pt;
    font-weight: 600;
    color: #f3f3f3;
}
QLabel#aboutVersion { color: #59b7ff; }

QLabel#quickStartTitle {
    font-size: 12pt;
    font-weight: 600;
    color: #f1f1f1;
}
QLabel#quickStartText, QLabel#aboutCredits { color: #c8c8c8; }
QPushButton#openUserGuideButton {
    background-color: #315f82;
    border-color: #5e8daf;
    font-weight: 600;
}
QPushButton#openUserGuideButton:hover { background-color: #3a7199; }

QListWidget#guideContents {
    background-color: #202326;
    border: 1px solid #454b50;
    padding: 6px;
}
QListWidget#guideContents::item {
    border: none;
    padding: 8px 10px;
    min-height: 20px;
}
QListWidget#guideContents::item:selected {
    background-color: #315f82;
    border: none;
}
QTextBrowser#guideBrowser {
    background-color: #1d2023;
    border: 1px solid #454b50;
    border-radius: 5px;
    padding: 12px;
}
QLineEdit#guideSearch {
    background-color: #202326;
    border: 1px solid #555d63;
    border-radius: 4px;
    padding: 6px;
}
"""


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Posterfolio")
    app.setOrganizationName("Posterfolio")
    icon_path = Path(__file__).resolve().parent / "assets" / "icons" / "posterfolio.ico"
    app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
