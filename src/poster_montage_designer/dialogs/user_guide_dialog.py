from __future__ import annotations

from html import escape

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices, QTextDocument
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


SECTIONS: list[tuple[str, str, str]] = [
    (
        "Welcome",
        "welcome",
        """
        <h1>Posterfolio User Guide</h1>
        <p>Posterfolio creates high-quality poster montages from your IMDb filmography.</p>
        <p>Import your credits, choose your preferred posters, arrange the layout, and export print-ready artwork.</p>
        <h2>What Posterfolio does</h2>
        <ul>
          <li>Imports credits from an IMDb person page.</li>
          <li>Finds poster artwork through The Movie Database (TMDb).</li>
          <li>Automatically fits posters to your chosen canvas size and aspect ratio.</li>
          <li>Lets you shuffle, rearrange, bench, replace and delete titles.</li>
          <li>Exports high-resolution PNG, JPEG, TIFF or PDF files.</li>
        </ul>
        """,
    ),
    (
        "Quick Start",
        "quick-start",
        """
        <h1>Quick Start</h1>
        <ol>
          <li>Add your TMDb API Read Access Token in <b>Edit → Settings</b>.</li>
          <li>Choose <b>File → Import from IMDb…</b> and open your IMDb person page.</li>
          <li>Import the credits, then shuffle, customise and export your montage.</li>
        </ol>
        <p>The first poster shown for each title is usually the best choice because Posterfolio prioritises English artwork with the strongest TMDb vote history.</p>
        """,
    ),
    (
        "TMDb API Token",
        "tmdb-token",
        """
        <h1>Getting a TMDb API Token</h1>
        <p>Posterfolio uses TMDb to find poster artwork. A free TMDb account and API Read Access Token are required.</p>
        <ol>
          <li>Visit <a href="https://www.themoviedb.org/">themoviedb.org</a> and create a free account.</li>
          <li>Open your TMDb account settings.</li>
          <li>Select <b>API</b>.</li>
          <li>Request a Developer API key if TMDb asks you to complete the API application.</li>
          <li>Copy the long value labelled <b>API Read Access Token</b>.</li>
          <li>In Posterfolio, choose <b>Edit → Settings…</b>.</li>
          <li>Paste the token into the TMDb token field and save.</li>
        </ol>
        <p>Your token is stored locally in Posterfolio's configuration on your computer.</p>
        <p><b>Important:</b> use the API Read Access Token, not your TMDb password.</p>
        """,
    ),
    (
        "Importing from IMDb",
        "imdb-import",
        """
        <h1>Importing IMDb Credits</h1>
        <p>Choose <b>File → Import from IMDb…</b>, or use the Import button in the Project panel.</p>
        <ol>
          <li>The embedded browser opens at IMDb.</li>
          <li>Navigate to the person's IMDb page.</li>
          <li>Open or expand the filmography if required.</li>
          <li>Press <b>Import Credits</b>.</li>
        </ol>
        <p>Posterfolio creates a new project, finds poster candidates through TMDb, downloads the selected posters and builds the canvas.</p>
        """,
    ),
    (
        "Choosing Posters",
        "choosing-posters",
        """
        <h1>Choosing Posters</h1>
        <p>Select a poster on the canvas. The selected title appears in the Project panel.</p>
        <p>Use the left and right arrows around <b>Poster 4 of 12</b> to browse alternatives.</p>
        <p>Posterfolio prefers English-language posters and sorts them by TMDb vote count, then vote average. This means the first choice is often the recognised theatrical artwork.</p>
        <p>Only the current poster choice is placed on the canvas, but nearby alternatives are quietly cached to make browsing faster.</p>
        """,
    ),
    (
        "The Bench",
        "bench",
        """
        <h1>The Bench</h1>
        <p>The Bench is a holding area for posters that are not currently on the canvas.</p>
        <p>A benched title is <b>not deleted</b>. It remains part of the project and can be returned to the montage later.</p>
        <ul>
          <li>Drag a canvas poster onto the Bench to remove it from the current layout.</li>
          <li>Drag a poster from the Bench onto a canvas poster to replace it.</li>
          <li>Right-click a benched poster for additional actions, including Promote, Open on IMDb and Delete from Project.</li>
        </ul>
        <p>The Bench is useful when a project contains more titles than fit attractively at the selected canvas size.</p>
        """,
    ),
    (
        "Automatic Layout",
        "layout",
        """
        <h1>Automatic Layout</h1>
        <p>Posterfolio calculates a layout that fits the available posters onto the selected canvas as effectively as possible.</p>
        <p>The arrangement is recalculated when you change:</p>
        <ul>
          <li>the canvas width or height;</li>
          <li>the canvas aspect ratio or preset;</li>
          <li>Airiness;</li>
          <li>the number of visible posters.</li>
        </ul>
        <p>The same posters may therefore be arranged differently on a portrait, landscape, square or cinematic canvas. This is expected: Posterfolio is seeking the best fit for the available shape.</p>
        <p><b>Arrange By</b> can order titles chronologically, by popularity or by box office. <b>Shuffle</b> generates a new random ordering and can be pressed repeatedly.</p>
        """,
    ),
    (
        "Canvas Size & Printing",
        "canvas-size",
        """
        <h1>Canvas Size and Printing</h1>
        <p>The Canvas menu includes common paper and screen proportions. You can also enter a custom width and height in millimetres.</p>
        <p>Many print shops offer a fixed list of standard sizes. A useful workflow is:</p>
        <ol>
          <li>Choose the print provider you intend to use.</li>
          <li>Check the sizes they can print.</li>
          <li>Choose a size and enter those dimensions in Posterfolio's Custom canvas fields.</li>
          <li>Review the recalculated layout before exporting.</li>
        </ol>
        <p>This lets you see how the montage will fit the real print before paying for production.</p>
        """,
    ),
    (
        "Airiness",
        "airiness",
        """
        <h1>Airiness</h1>
        <p>Airiness controls the amount of space around and between posters.</p>
        <ul>
          <li><b>Lower values</b> create a tighter layout with larger posters.</li>
          <li><b>Higher values</b> introduce more breathing room and a more spacious presentation.</li>
        </ul>
        <p>Choose the canvas size first, then adjust Airiness. Because Airiness changes the usable space, it may alter the grid and can move titles to or from the Bench.</p>
        """,
    ),
    (
        "Canvas Colour",
        "canvas-colour",
        """
        <h1>Canvas Colour</h1>
        <p>The canvas colour is the background visible between posters and around the montage.</p>
        <p>Use <b>Canvas Colour…</b> to choose a new colour. Dark backgrounds often work well with film posters, while neutral or light backgrounds can produce a cleaner print style.</p>
        """,
    ),
    (
        "Projects & Menus",
        "projects-menus",
        """
        <h1>Projects and Menus</h1>
        <h2>File menu</h2>
        <ul>
          <li><b>New Project</b> clears the current project.</li>
          <li><b>Open Project…</b> opens a Posterfolio <code>.pmd</code> file.</li>
          <li><b>Save Project</b> saves to the current project file.</li>
          <li><b>Save Project As…</b> saves a new copy.</li>
          <li><b>Import from IMDb…</b> opens the embedded IMDb importer.</li>
          <li><b>Export…</b> renders the finished montage.</li>
        </ul>
        <h2>Edit menu</h2>
        <ul>
          <li><b>Undo / Redo</b> reverses project edits.</li>
          <li><b>Settings…</b> stores the TMDb token and application preferences.</li>
        </ul>
        <h2>Project files</h2>
        <p>A <code>.pmd</code> file stores the title list, selected poster choices, Bench state, canvas settings, layout order and other project information. Poster image files are cached separately.</p>
        """,
    ),
    (
        "Exporting & Rendering",
        "exporting",
        """
        <h1>Exporting and Rendering</h1>
        <p>Choose <b>File → Export…</b> after the layout is ready.</p>
        <p>Posterfolio renders from the downloaded source poster images. The small previews in the interface are only for display; the export is not made by enlarging the on-screen thumbnails.</p>
        <p>The export dialog shows the maximum practical pixel dimensions for the current source material. Use the size slider to reduce the output when a smaller file is sufficient.</p>
        <p>Available formats include PNG, JPEG, TIFF and PDF. The exact options shown depend on the current build.</p>
        <h2>Where files go</h2>
        <p>After choosing Export, Posterfolio asks where to save the rendered file. The chosen location becomes the default folder for the next export.</p>
        <p>The rendered image or PDF is separate from the <code>.pmd</code> project file. Saving a project does not automatically render an image, and exporting does not replace the project.</p>
        """,
    ),
    (
        "Tips & Shortcuts",
        "tips",
        """
        <h1>Tips and Shortcuts</h1>
        <ul>
          <li><b>F1</b> opens this User Guide.</li>
          <li>Select a poster on the canvas to browse alternative artwork.</li>
          <li>Press Shuffle several times to quickly explore different arrangements.</li>
          <li>Use the Bench rather than deleting titles while experimenting.</li>
          <li>Set the final print size before fine-tuning Airiness.</li>
          <li>Export at the largest practical size when preparing a high-quality print.</li>
          <li>Middle-mouse drag pans the canvas; the mouse wheel zooms it.</li>
          <li>Press <b>F</b> while the canvas has focus to fit the page to the window.</li>
        </ul>
        """,
    ),
    (
        "Credits",
        "credits",
        """
        <h1>Credits</h1>
        <p><b>Posterfolio 1.0</b></p>
        <p>Designed and written by Charles Tait.</p>
        <p>Built with Python and Qt.</p>
        <p>Poster images and metadata are provided by TMDb. IMDb is used to identify filmography titles.</p>
        """,
    ),
]


class UserGuideDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Posterfolio User Guide")
        self.resize(980, 700)
        self.setMinimumSize(760, 520)

        self.contents = QListWidget(self)
        self.contents.setObjectName("guideContents")
        self.contents.setFixedWidth(210)

        self.browser = QTextBrowser(self)
        self.browser.setObjectName("guideBrowser")
        self.browser.setOpenExternalLinks(False)
        self.browser.anchorClicked.connect(self._open_link)

        self.search = QLineEdit(self)
        self.search.setObjectName("guideSearch")
        self.search.setPlaceholderText("Search this section…")
        self.search.returnPressed.connect(self._find_next)
        find_button = QPushButton("Find Next", self)
        find_button.clicked.connect(self._find_next)
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search"))
        search_row.addWidget(self.search, 1)
        search_row.addWidget(find_button)

        right_layout = QVBoxLayout()
        right_layout.addLayout(search_row)
        right_layout.addWidget(self.browser, 1)

        main_row = QHBoxLayout()
        main_row.addWidget(self.contents)
        main_row.addLayout(right_layout, 1)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        root.addLayout(main_row, 1)
        root.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)

        for title, anchor, _html in SECTIONS:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, anchor)
            self.contents.addItem(item)

        self.contents.currentRowChanged.connect(self._show_section)
        self.contents.setCurrentRow(0)

    def _show_section(self, row: int) -> None:
        if row < 0 or row >= len(SECTIONS):
            return
        title, _anchor, body = SECTIONS[row]
        html = f"""
        <html><head><style>
          body {{ font-family: 'Segoe UI'; font-size: 10.5pt; color: #d8d8d8; line-height: 1.35; }}
          h1 {{ color: #f2f2f2; font-size: 22pt; margin-bottom: 12px; }}
          h2 {{ color: #8dc8ff; font-size: 14pt; margin-top: 20px; }}
          a {{ color: #72bdf3; }}
          code {{ color: #b9dcf5; background: #22272b; }}
          li {{ margin-bottom: 6px; }}
        </style></head><body>{body}</body></html>
        """
        self.browser.setHtml(html)
        self.search.clear()

    def _find_next(self) -> None:
        text = self.search.text().strip()
        if not text:
            return
        if not self.browser.find(text):
            cursor = self.browser.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            self.browser.setTextCursor(cursor)
            self.browser.find(text)

    def _open_link(self, url: QUrl) -> None:
        if url.scheme() in {"http", "https"}:
            QDesktopServices.openUrl(url)
