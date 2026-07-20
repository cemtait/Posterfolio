from __future__ import annotations
import json
import re
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QMenu,
    QPushButton,
    QVBoxLayout,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from poster_montage_designer.models import Title
from poster_montage_designer.services.imdb_capture import (
    IMDB_CREDIT_CAPTURE_SCRIPT,
    titles_from_capture,
)


DEVELOPER_MODE = False

IMDB_PERSON_RE = re.compile(r"https?://(?:www\.)?imdb\.com/name/nm\d+", re.IGNORECASE)


class ImdbImportDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Import from IMDb")
        self.resize(1100, 760)

        self._titles: list[Title] = []
        self._source_url = "https://www.imdb.com/"

        self.browser = QWebEngineView(self)
        self.url_edit = QLineEdit(self)
        self.url_edit.setText(self._source_url)

        self.back_button = QPushButton("Back", self)
        self.forward_button = QPushButton("Forward", self)
        self.reload_button = QPushButton("Reload", self)
        self.go_button = QPushButton("Go", self)
        self.developer_button = QPushButton("Developer", self)
        self.developer_menu = QMenu(self.developer_button)
        self.developer_button.setMenu(self.developer_menu)
        self.developer_button.setVisible(DEVELOPER_MODE)

        self.dump_html_action = self.developer_menu.addAction("Dump Page HTML...")
        self.dump_next_data_action = self.developer_menu.addAction("Dump __NEXT_DATA__...")
        self.dump_links_action = self.developer_menu.addAction("Dump Visible Links...")

        self.status_label = QLabel("Open an IMDb person page to enable Import Credits.", self)
        self.status_label.setWordWrap(True)

        self.import_button = QPushButton("Import Credits", self)
        self.import_button.setEnabled(False)
        self.cancel_button = QPushButton("Cancel", self)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.back_button)
        toolbar.addWidget(self.forward_button)
        toolbar.addWidget(self.reload_button)
        toolbar.addWidget(self.url_edit, 1)
        toolbar.addWidget(self.go_button)
        toolbar.addWidget(self.developer_button)

        footer = QHBoxLayout()
        footer.addWidget(self.status_label, 1)
        footer.addWidget(self.cancel_button)
        footer.addWidget(self.import_button)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self.browser, 1)
        layout.addLayout(footer)

        self.back_button.clicked.connect(self.browser.back)
        self.forward_button.clicked.connect(self.browser.forward)
        self.reload_button.clicked.connect(self.browser.reload)
        self.go_button.clicked.connect(self._go_to_url)
        self.url_edit.returnPressed.connect(self._go_to_url)
        self.cancel_button.clicked.connect(self.reject)
        self.import_button.clicked.connect(self._capture_credits)

        self.dump_html_action.triggered.connect(self._dump_page_html)
        self.dump_next_data_action.triggered.connect(self._dump_next_data)
        self.dump_links_action.triggered.connect(self._dump_visible_links)

        self.browser.urlChanged.connect(self._url_changed)
        self.browser.loadStarted.connect(self._load_started)
        self.browser.loadFinished.connect(self._load_finished)

        self.browser.setUrl(QUrl(self._source_url))

    def imported_titles(self) -> list[Title]:
        return self._titles

    def import_source_label(self) -> str:
        return f"IMDb page: {self._source_url}"

    def _go_to_url(self) -> None:
        text = self.url_edit.text().strip()
        if not text:
            return
        if not text.startswith(("http://", "https://")):
            text = "https://" + text
        self.browser.setUrl(QUrl(text))

    def _url_changed(self, url: QUrl) -> None:
        text = url.toString()
        self._source_url = text
        self.url_edit.setText(text)
        self._update_import_state()

    def _load_started(self) -> None:
        self.status_label.setText("Loading IMDb page...")
        self.import_button.setEnabled(False)

    def _load_finished(self, ok: bool) -> None:
        if not ok:
            self.status_label.setText("Page failed to load.")
            self.import_button.setEnabled(False)
            return
        self._update_import_state()

    def _update_import_state(self) -> None:
        is_person_page = bool(IMDB_PERSON_RE.match(self._source_url))
        self.import_button.setEnabled(is_person_page)
        if is_person_page:
            self.status_label.setText("IMDb person page detected. Click Import Credits when the credits are visible.")
        else:
            self.status_label.setText("Open an IMDb person page to enable Import Credits.")

    def _capture_credits(self) -> None:
        self.import_button.setEnabled(False)
        self.status_label.setText("Capturing credits from the current IMDb page...")
        self.browser.page().runJavaScript(IMDB_CREDIT_CAPTURE_SCRIPT, self._credits_captured)

    def _credits_captured(self, result) -> None:
        raw_items = json.loads(result) if isinstance(result, str) and result else []
        self._titles = titles_from_capture(raw_items)

        if not self._titles:
            self.status_label.setText("No credits were found on this page.")
            self.import_button.setEnabled(True)
            QMessageBox.warning(
                self,
                "No Credits Found",
                "Posterfolio could not find IMDb title credits on this page. Make sure you are on an IMDb person page and try again.",
            )
            return

        self.status_label.setText(f"Imported {len(self._titles)} IMDb credits.")
        self.accept()

    # ------------------------------------------------------------------
    # Developer diagnostics

    def _safe_dump_stem(self) -> str:
        match = re.search(r"/name/(nm\d+)", self._source_url)
        if match:
            return f"imdb_{match.group(1)}"
        return "imdb_page"

    def _choose_dump_path(self, title: str, default_name: str, file_filter: str) -> Path | None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            title,
            f"exports/{default_name}",
            file_filter,
        )
        if not file_path:
            return None
        return Path(file_path)

    def _write_dump(self, path: Path, text: str, label: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text or "", encoding="utf-8")
        self.status_label.setText(f"Saved {label}: {path.name}")
        QMessageBox.information(self, "Dump Saved", f"Saved {label}:\n{path}")

    def _dump_page_html(self) -> None:
        path = self._choose_dump_path(
            "Dump Page HTML",
            f"{self._safe_dump_stem()}_page.html",
            "HTML Files (*.html);;Text Files (*.txt);;All Files (*.*)",
        )
        if path is None:
            return

        self.status_label.setText("Dumping page HTML...")
        self.browser.page().toHtml(lambda html: self._write_dump(path, html, "page HTML"))

    def _dump_next_data(self) -> None:
        path = self._choose_dump_path(
            "Dump IMDb JSON Data",
            f"{self._safe_dump_stem()}_next_data.json",
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*.*)",
        )
        if path is None:
            return

        script = r'''
(() => {
  const direct = document.getElementById('__NEXT_DATA__')?.textContent;
  if (direct && direct.trim()) return direct;

  const blobs = [];
  for (const script of document.querySelectorAll('script')) {
    const text = script.textContent || '';
    if (!text.includes('tt') && !text.includes('nm')) continue;
    if (script.type === 'application/json' || script.type === 'application/ld+json') {
      blobs.push({ id: script.id || '', type: script.type || '', text });
    }
  }

  return JSON.stringify({
    url: window.location.href,
    title: document.title,
    blobs,
  }, null, 2);
})();
'''
        self.status_label.setText("Dumping IMDb JSON data...")
        self.browser.page().runJavaScript(
            script,
            lambda text: self._write_dump(path, str(text or ""), "IMDb JSON data"),
        )

    def _dump_visible_links(self) -> None:
        path = self._choose_dump_path(
            "Dump Visible Links",
            f"{self._safe_dump_stem()}_visible_links.json",
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*.*)",
        )
        if path is None:
            return

        script = r'''
(() => {
  const links = Array.from(document.querySelectorAll('a[href]')).map((a, index) => ({
    index,
    href: a.href || a.getAttribute('href') || '',
    text: (a.innerText || a.textContent || '').replace(/\s+/g, ' ').trim(),
    ariaLabel: a.getAttribute('aria-label') || '',
  }));

  return JSON.stringify({
    url: window.location.href,
    title: document.title,
    linkCount: links.length,
    titleLinkCount: links.filter(link => link.href.includes('/title/tt')).length,
    links,
    bodyTextLength: (document.body?.innerText || '').length,
  }, null, 2);
})();
'''
        self.status_label.setText("Dumping visible links...")
        self.browser.page().runJavaScript(
            script,
            lambda text: self._write_dump(path, str(text or ""), "visible links"),
        )
