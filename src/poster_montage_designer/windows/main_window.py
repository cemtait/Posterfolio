from __future__ import annotations

import json
import random
from copy import deepcopy
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint, QSettings, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QBrush, QColor, QDesktopServices, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QSlider,
    QSplitter,
    QVBoxLayout,
)

from poster_montage_designer.config import AppConfig, load_config, save_config
from poster_montage_designer.dialogs.about_dialog import AboutDialog, AboutOverlay
from poster_montage_designer.dialogs.export_dialog import ExportDialog
from poster_montage_designer.dialogs.imdb_import_dialog import ImdbImportDialog
from poster_montage_designer.dialogs.user_guide_dialog import UserGuideDialog
from poster_montage_designer.dialogs.settings_dialog import SettingsDialog
from poster_montage_designer.version import APP_VERSION
from poster_montage_designer.io.imdb import import_imdb_json
from poster_montage_designer.layouts.grid import GridLayout, calculate_grid_layout
from poster_montage_designer.models import Project, Title
from poster_montage_designer.services.posters import (
    get_poster,
    get_poster_candidate_count,
    prefetch_poster_neighbors,
)
from poster_montage_designer.services.render import render_project_image
from poster_montage_designer.services.tmdb import lookup_imdb_id
from poster_montage_designer.ui.ui_main_window import Ui_MainWindow
from poster_montage_designer.widgets.title_list import DraggableTitleList
from poster_montage_designer.widgets.workspace import WorkspaceView


MM_PER_INCH = 25.4
DEFAULT_PAGE_WIDTH_MM = 27.0 * MM_PER_INCH
DEFAULT_PAGE_HEIGHT_MM = 40.0 * MM_PER_INCH

CANVAS_PRESETS: dict[str, tuple[float, float]] = {
    "One Sheet 27 × 40 in": (27.0 * MM_PER_INCH, 40.0 * MM_PER_INCH),
    "A3 Portrait": (297.0, 420.0),
    "A3 Landscape": (420.0, 297.0),
    "A2 Portrait": (420.0, 594.0),
    "A2 Landscape": (594.0, 420.0),
    "16:9 Projection": (1016.0, 571.5),
    "4:3 Projection": (1016.0, 762.0),
    "2.39:1 CinemaScope": (1016.0, 425.1),
    "1:1 Square": (800.0, 800.0),
    "Custom": (DEFAULT_PAGE_WIDTH_MM, DEFAULT_PAGE_HEIGHT_MM),
}



class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        icon_path = Path(__file__).resolve().parents[1] / "assets" / "icons" / "posterfolio.ico"
        self.setWindowIcon(QIcon(str(icon_path)))

        self.settings = QSettings("Posterfolio", "Posterfolio")
        self.project = Project()
        self.poster_entries: list[tuple[str, Path]] = []
        self.current_layout: GridLayout | None = None
        self.visible_imdb_ids: list[str] = []
        self._updating_canvas_controls = False
        self._restoring_history = False
        self.undo_stack: list[Project] = []
        self.redo_stack: list[Project] = []

        self.create_from_imdb_button = QPushButton("Import from IMDb...", self.ui.projectPanel)
        self.arrange_button = QPushButton("Arrange By", self.ui.projectPanel)
        self.arrange_menu = QMenu(self.arrange_button)
        self.arrange_button.setMenu(self.arrange_menu)
        self.arrange_menu.addAction("Chronological", self.sort_chronological)
        self.arrange_menu.addAction("Popularity", self.sort_popularity)
        self.arrange_menu.addAction("Box Office", self.sort_box_office)
        self.shuffle_button = QPushButton("Shuffle", self.ui.projectPanel)
        self.bench_selected_button = QPushButton("Bench Selected", self.ui.projectPanel)
        self.promote_selected_button = QPushButton("Promote Selected", self.ui.projectPanel)
        self.swap_selected_button = QPushButton("Swap Selected", self.ui.projectPanel)
        self.clear_bench_button = QPushButton("Clear Bench...", self.ui.projectPanel)
        self.swap_selected_button.setEnabled(False)

        self.workspace = WorkspaceView(self.ui.canvasPanel)
        self.title_list = DraggableTitleList("active", self.ui.projectPanel)
        self.bench_list = DraggableTitleList("bench", self.ui.projectPanel)
        self.project_summary_label = QLabel("", self.ui.projectPanel)
        self.progress_label = QLabel("", self.ui.projectPanel)
        self.progress_bar = QProgressBar(self.ui.projectPanel)

        self.poster_preview_label = QLabel(self.ui.propertiesPanel)
        self.poster_controls_layout = QHBoxLayout()
        self.previous_poster_button = QPushButton("<", self.ui.propertiesPanel)
        self.poster_counter_label = QLabel("0 / 0", self.ui.propertiesPanel)
        self.next_poster_button = QPushButton(">", self.ui.propertiesPanel)

        self.airiness_label = QLabel("Airiness: 50", self.ui.propertiesPanel)
        self.airiness_slider = QSlider(Qt.Orientation.Horizontal, self.ui.propertiesPanel)
        self.canvas_preset_combo = QComboBox(self.ui.propertiesPanel)
        self.canvas_width_spin = QDoubleSpinBox(self.ui.propertiesPanel)
        self.canvas_height_spin = QDoubleSpinBox(self.ui.propertiesPanel)
        self.canvas_color_button = QPushButton("Canvas Colour...", self.ui.propertiesPanel)

        self._install_menus()
        self._install_splitter()
        self._install_workspace()
        self.about_overlay = AboutOverlay(self.workspace.viewport())
        self.about_overlay.user_guide_requested.connect(self.show_user_guide)
        self._install_project_panel_widgets()
        self._install_properties_panel_widgets()
        self._install_title_context_menus()
        self._restore_application_state()

        self.ui.newMontageButton.hide()
        self.ui.openMontageButton.hide()
        self.ui.projectStatusLabel.hide()
        self.ui.propertiesStatusLabel.hide()

        self.create_from_imdb_button.clicked.connect(self.import_from_imdb_page)
        self.shuffle_button.clicked.connect(self.shuffle_layout)
        self.bench_selected_button.clicked.connect(self.bench_selected_titles)
        self.promote_selected_button.clicked.connect(self.promote_selected_titles)
        self.swap_selected_button.clicked.connect(self.swap_selected_titles)
        self.title_list.currentItemChanged.connect(self._title_selection_changed)
        self.title_list.itemSelectionChanged.connect(self._update_swap_button_state)
        self.bench_list.itemSelectionChanged.connect(self._update_swap_button_state)
        self.previous_poster_button.clicked.connect(self.previous_poster)
        self.next_poster_button.clicked.connect(self.next_poster)
        self.airiness_slider.valueChanged.connect(self._airiness_changed)
        self.canvas_color_button.clicked.connect(self.choose_canvas_color)
        self.canvas_preset_combo.currentTextChanged.connect(self._canvas_preset_changed)
        self.canvas_width_spin.valueChanged.connect(self._manual_canvas_size_changed)
        self.canvas_height_spin.valueChanged.connect(self._manual_canvas_size_changed)
        self.workspace.poster_selected.connect(self._workspace_poster_selected)
        self.workspace.poster_swap_requested.connect(self._workspace_poster_swap_requested)
        self.workspace.bench_poster_replace_requested.connect(self._bench_poster_replace_requested)
        self.workspace.bench_posters_promote_requested.connect(self._promote_bench_ids)
        self.workspace.context_menu_requested.connect(self._show_workspace_context_menu)
        self.workspace.canvas_drag_released.connect(self._canvas_drag_released)
        self.bench_list.canvas_titles_dropped.connect(self._canvas_posters_benched)
        self.bench_list.canvas_poster_swap_requested.connect(self._canvas_bench_poster_swap_requested)
        self.bench_list.delete_requested.connect(self.delete_selected_titles)
        self.workspace.delete_requested.connect(self.delete_selected_titles)
        self.workspace.selection_changed.connect(self._workspace_selection_changed)
        self.clear_bench_button.clicked.connect(self.clear_bench)

        self.workspace.set_canvas_color(self.project.canvas_color)
        self._sync_canvas_controls_from_project()
        self._refresh_all(rebuild=False)
        QTimer.singleShot(0, self.about_overlay.reposition)

    def _install_menus(self) -> None:
        file_menu = self.menuBar().addMenu("File")

        new_action = QAction("New Project", self)
        open_action = QAction("Open Project...", self)
        save_action = QAction("Save Project", self)
        save_as_action = QAction("Save Project As...", self)
        import_page_action = QAction("Import from IMDb...", self)
        export_action = QAction("Export...", self)
        exit_action = QAction("Exit", self)

        new_action.triggered.connect(self.new_montage)
        open_action.triggered.connect(self.open_montage)
        save_action.triggered.connect(self.save_montage)
        save_as_action.triggered.connect(self.save_montage_as)
        import_page_action.triggered.connect(self.import_from_imdb_page)
        export_action.triggered.connect(self.export_image)
        exit_action.triggered.connect(self.close)

        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(import_page_action)
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        edit_menu = self.menuBar().addMenu("Edit")

        self.undo_action = QAction("Undo", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self.undo)
        self.undo_action.setEnabled(False)

        self.redo_action = QAction("Redo", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(self.redo)
        self.redo_action.setEnabled(False)

        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self.open_settings)

        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(settings_action)

        help_menu = self.menuBar().addMenu("Help")

        user_guide_action = QAction("User Guide...", self)
        user_guide_action.setShortcut(QKeySequence(Qt.Key.Key_F1))
        user_guide_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        user_guide_action.triggered.connect(self.show_user_guide)

        about_action = QAction("About Posterfolio...", self)
        about_action.triggered.connect(self.show_about_dialog)

        help_menu.addAction(user_guide_action)
        help_menu.addSeparator()
        help_menu.addAction(about_action)

    def _install_splitter(self) -> None:
        self.ui.mainLayout.removeWidget(self.ui.projectPanel)
        self.ui.mainLayout.removeWidget(self.ui.canvasPanel)
        self.ui.mainLayout.removeWidget(self.ui.propertiesPanel)

        self.ui.projectPanel.setMinimumWidth(340)
        self.ui.projectPanel.setMaximumWidth(520)
        self.ui.canvasPanel.setMinimumWidth(520)
        self.ui.propertiesPanel.hide()

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self.ui.centralwidget)
        self.splitter.setObjectName("mainSplitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.ui.projectPanel)
        self.splitter.addWidget(self.ui.canvasPanel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([400, 920])
        self.ui.mainLayout.addWidget(self.splitter)

    def _install_workspace(self) -> None:
        if not isinstance(self.ui.canvasLayout, QVBoxLayout):
            raise RuntimeError("canvasPanel must have a QVBoxLayout.")

        self.ui.canvasLayout.removeWidget(self.ui.canvasPlaceholderLabel)
        self.ui.canvasPlaceholderLabel.deleteLater()
        self.ui.canvasLayout.setContentsMargins(0, 0, 0, 0)
        self.ui.canvasLayout.setSpacing(0)
        self.ui.canvasLayout.addWidget(self.workspace)

        self.progress_popup = QFrame(self.workspace.viewport())
        self.progress_popup.setObjectName("progressPopup")
        self.progress_popup.setFixedWidth(390)
        popup_layout = QVBoxLayout(self.progress_popup)
        popup_layout.setContentsMargins(14, 12, 14, 12)
        popup_layout.setSpacing(7)
        popup_layout.addWidget(self.progress_label)
        popup_layout.addWidget(self.progress_bar)
        self.progress_popup.hide()

    def _install_project_panel_widgets(self) -> None:
        if not isinstance(self.ui.projectLayout, QVBoxLayout):
            raise RuntimeError("projectPanel must have a QVBoxLayout.")

        self.progress_label.setObjectName("progressLabel")
        self.progress_label.setWordWrap(True)
        self.progress_label.setMinimumHeight(38)
        self.progress_bar.setObjectName("projectProgressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        self._clear_progress()

        bench_list_title = QLabel("Bench", self.ui.projectPanel)
        bench_list_title.setObjectName("benchListTitleLabel")

        self.title_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.title_list.hide()

        self.bench_list.setObjectName("benchPosterList")
        self.bench_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.bench_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bench_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.bench_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.bench_list.setFlow(QListWidget.Flow.LeftToRight)
        self.bench_list.setWrapping(True)
        self.bench_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.bench_list.setMovement(QListView.Movement.Static)
        self.bench_list.setUniformItemSizes(True)
        self.bench_list.setSpacing(0)
        self.bench_list.setIconSize(QSize(66, 99))
        self.bench_list.setGridSize(QSize(78, 112))
        self.bench_list.setWordWrap(False)
        self.bench_list.setMinimumHeight(135)
        self.bench_list.setMaximumHeight(250)

        layout_buttons = QHBoxLayout()
        layout_buttons.addWidget(self.arrange_button, 1)
        layout_buttons.addWidget(self.shuffle_button)

        self.project_summary_label.setObjectName("projectSummaryLabel")
        self.project_summary_label.setWordWrap(True)

        self.ui.projectLayout.insertWidget(3, self.create_from_imdb_button)
        self.ui.projectLayout.insertLayout(4, layout_buttons)
        self.ui.projectLayout.insertWidget(5, self.project_summary_label)
        self.ui.projectLayout.insertWidget(6, bench_list_title)
        self.ui.projectLayout.insertWidget(7, self.bench_list, 1)
        self.ui.projectLayout.insertWidget(8, self.clear_bench_button)

        self.bench_selected_button.hide()
        self.promote_selected_button.hide()
        self.swap_selected_button.hide()
        self.clear_bench_button.setEnabled(False)

    def _install_title_context_menus(self) -> None:
        for widget in (self.title_list, self.bench_list):
            widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.title_list.customContextMenuRequested.connect(self._show_title_list_context_menu)
        self.bench_list.customContextMenuRequested.connect(self._show_bench_list_context_menu)

    def _restore_application_state(self) -> None:
        geometry = self.settings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

        splitter_state = self.settings.value("window/splitter_state_v2")
        if splitter_state is not None:
            self.splitter.restoreState(splitter_state)

    def closeEvent(self, event) -> None:
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/splitter_state_v2", self.splitter.saveState())
        super().closeEvent(event)

    def _install_properties_panel_widgets(self) -> None:
        selected_title = QLabel("Selected Poster", self.ui.projectPanel)
        selected_title.setObjectName("propertiesTitleLabel")

        for widget in (self.poster_preview_label, self.previous_poster_button, self.poster_counter_label,
                       self.next_poster_button, self.airiness_label, self.airiness_slider,
                       self.canvas_preset_combo, self.canvas_width_spin, self.canvas_height_spin,
                       self.canvas_color_button):
            widget.setParent(self.ui.projectPanel)

        self.poster_preview_label.setObjectName("posterPreviewLabel")
        self.poster_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Keep the preview area stable so changing the selected title never
        # changes the Project panel geometry. The poster fills the available
        # width while preserving its aspect ratio.
        self.poster_preview_label.setFixedHeight(430)
        self.poster_preview_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

        self.poster_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.poster_controls_layout.addWidget(self.previous_poster_button)
        self.poster_controls_layout.addWidget(self.poster_counter_label, 1)
        self.poster_controls_layout.addWidget(self.next_poster_button)

        self.airiness_slider.setRange(0, 100)
        self.airiness_slider.setValue(self.project.airiness)
        for name in CANVAS_PRESETS:
            self.canvas_preset_combo.addItem(name)
        for spin in (self.canvas_width_spin, self.canvas_height_spin):
            spin.setRange(50.0, 3000.0)
            spin.setDecimals(1)
            spin.setSingleStep(5.0)
            spin.setSuffix(" mm")

        canvas_size_form = QFormLayout()
        canvas_size_form.setContentsMargins(0, 0, 0, 0)
        canvas_size_form.addRow("Canvas", self.canvas_preset_combo)
        canvas_size_form.addRow("Width", self.canvas_width_spin)
        canvas_size_form.addRow("Height", self.canvas_height_spin)

        # Insert the selected-poster and canvas controls above the Bench tray.
        self.ui.projectLayout.insertWidget(6, selected_title)
        self.ui.projectLayout.insertWidget(7, self.poster_preview_label)
        self.ui.projectLayout.insertLayout(8, self.poster_controls_layout)
        self.ui.projectLayout.insertLayout(9, canvas_size_form)
        self.ui.projectLayout.insertWidget(10, self.airiness_label)
        self.ui.projectLayout.insertWidget(11, self.airiness_slider)
        self.ui.projectLayout.insertWidget(12, self.canvas_color_button)

    # ------------------------------------------------------------------
    # File / project commands

    def new_montage(self) -> None:
        self._push_undo()
        self.project = Project()
        self.poster_entries.clear()
        self.current_layout = None
        self.visible_imdb_ids.clear()
        self.workspace.set_page_size(self.project.page_width_mm, self.project.page_height_mm)
        self.workspace.set_canvas_color(self.project.canvas_color)
        self.airiness_slider.setValue(self.project.airiness)
        self._sync_canvas_controls_from_project()
        self._refresh_all(rebuild=False)
        self.about_overlay.show_immediately()

    def open_montage(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            self._last_project_directory(),
            "Posterfolio Projects (*.pmd);;JSON Files (*.json);;All Files (*.*)",
        )
        if file_path:
            path = Path(file_path)
            self._remember_project_directory(path.parent)
            self._load_project_file(path)

    def save_montage(self) -> None:
        if self.project.path is None:
            self.save_montage_as()
            return
        self._save_project_file(self.project.path)

    def save_montage_as(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            str(Path(self._last_project_directory()) / "untitled_project.pmd"),
            "Posterfolio Projects (*.pmd);;JSON Files (*.json);;All Files (*.*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        if path.suffix.lower() == "":
            path = path.with_suffix(".pmd")
        self.project.path = path
        self._remember_project_directory(path.parent)
        self._save_project_file(path)

    def open_settings(self) -> None:
        SettingsDialog(self).exec()

    def show_user_guide(self) -> None:
        UserGuideDialog(self).exec()

    def show_about_dialog(self) -> None:
        dialog = AboutDialog(self)
        dialog.user_guide_requested.connect(self.show_user_guide)
        dialog.exec()

    def _last_project_directory(self) -> str:
        return str(self.settings.value("folders/project", "projects"))

    def _remember_project_directory(self, path: Path) -> None:
        self.settings.setValue("folders/project", str(path))

    def _last_export_directory(self) -> str:
        return str(self.settings.value("folders/export", "exports"))

    def _remember_export_directory(self, path: Path) -> None:
        self.settings.setValue("folders/export", str(path))

    def import_from_imdb_page(self) -> None:
        dialog = ImdbImportDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        titles = dialog.imported_titles()
        if not titles:
            self.statusBar().showMessage("No IMDb credits were captured.")
            return

        self._push_undo()
        self.project = Project()
        self.project.titles = titles
        self.project.layout_order = [
            title.imdb_title_id for title in self.project.titles if title.imdb_title_id
        ]
        self.project.source = dialog.import_source_label()
        self.project.dirty = True
        self.poster_entries.clear()
        self.current_layout = None
        self.visible_imdb_ids.clear()
        self.workspace.clear_posters()

        if self.project.name in {"Untitled Montage", "Untitled Project"}:
            self.project.name = "IMDb Project"

        self._refresh_all(rebuild=False)
        self.load_posters()

    def create_from_imdb_json(self) -> None:
        if self.import_imdb_json():
            self.load_posters()

    def import_imdb_json(self) -> bool:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import IMDb JSON",
            "projects",
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not file_path:
            return False

        self._push_undo()
        self.project = Project()
        self._set_progress("Importing IMDb JSON...", 0, 100)
        QApplication.processEvents()

        self.project.titles = import_imdb_json(file_path)
        self.project.layout_order = [
            title.imdb_title_id for title in self.project.titles if title.imdb_title_id
        ]
        self.project.source = str(Path(file_path).name)
        self.project.dirty = True
        self.poster_entries.clear()
        self.current_layout = None
        self.visible_imdb_ids.clear()
        self.workspace.clear_posters()

        if self.project.name in {"Untitled Montage", "Untitled Project"}:
            self.project.name = "IMDb Project"

        self._clear_progress()
        self._refresh_all(rebuild=False)
        return True

    def export_image(self) -> None:
        if self.current_layout is None or not self.visible_imdb_ids:
            self.statusBar().showMessage("Load posters before exporting.")
            return

        dialog = ExportDialog(
            project=self.project,
            layout=self.current_layout,
            visible_imdb_ids=self.visible_imdb_ids,
            parent=self,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Image",
            str(Path(self._last_export_directory()) / Path(dialog.default_output_path()).name),
            dialog.file_filter(),
        )
        if not file_path:
            return

        output_path = Path(file_path)
        self._remember_export_directory(output_path.parent)
        if output_path.suffix.lower() == "":
            output_path = output_path.with_suffix(dialog.default_suffix())

        def progress(message: str, value: int, maximum: int) -> None:
            self._set_progress(message, value, maximum)
            QApplication.processEvents()

        try:
            render_project_image(
                project=self.project,
                layout=self.current_layout,
                visible_imdb_ids=self.visible_imdb_ids,
                output_path=output_path,
                width_px=dialog.export_width_px(),
                output_format=dialog.output_format(),
                progress_callback=progress,
            )

            self._set_progress("Export complete.", 1, 1)
            QApplication.processEvents()
            self.statusBar().showMessage(f"Exported {output_path.name}")

        finally:
            self._clear_progress()

    # ------------------------------------------------------------------
    # Undo / redo

    def _push_undo(self) -> None:
        if self._restoring_history:
            return
        self.undo_stack.append(deepcopy(self.project))
        self.redo_stack.clear()
        self._update_history_actions()

    def undo(self) -> None:
        if not self.undo_stack:
            return
        self._restoring_history = True
        self.redo_stack.append(deepcopy(self.project))
        self.project = self.undo_stack.pop()
        self.project.dirty = True
        self._restore_project_to_ui()
        self._restoring_history = False
        self._update_history_actions()

    def redo(self) -> None:
        if not self.redo_stack:
            return
        self._restoring_history = True
        self.undo_stack.append(deepcopy(self.project))
        self.project = self.redo_stack.pop()
        self.project.dirty = True
        self._restore_project_to_ui()
        self._restoring_history = False
        self._update_history_actions()

    def _update_history_actions(self) -> None:
        self.undo_action.setEnabled(bool(self.undo_stack))
        self.redo_action.setEnabled(bool(self.redo_stack))

    def _restore_project_to_ui(self) -> None:
        self.workspace.set_page_size(self.project.page_width_mm, self.project.page_height_mm)
        self.workspace.set_canvas_color(self.project.canvas_color)
        self.airiness_slider.setValue(self.project.airiness)
        self._sync_canvas_controls_from_project()
        self._refresh_all(rebuild=True)

    # ------------------------------------------------------------------
    # Layout commands

    def sort_chronological(self) -> None:
        self._push_undo()
        titles = self.project.active_titles
        self._ensure_metadata_for_titles(titles, "Checking dates")
        ordered = sorted(titles, key=lambda title: (title.year is None, -(title.year or 0), title.title.lower()))
        self._set_layout_order_from_titles(ordered)
        self.statusBar().showMessage("Sorted newest first.")

    def sort_popularity(self) -> None:
        self._push_undo()
        titles = self.project.active_titles
        self._ensure_metadata_for_titles(titles, "Checking popularity")
        ordered = sorted(
            titles,
            key=lambda title: (
                title.popularity is None,
                -(title.popularity or 0.0),
                title.title.lower(),
            ),
        )
        self._set_layout_order_from_titles(ordered)
        self.statusBar().showMessage("Sorted by TMDb popularity.")

    def sort_box_office(self) -> None:
        self._push_undo()
        titles = self.project.active_titles
        self._ensure_metadata_for_titles(titles, "Checking box office")
        ordered = sorted(titles, key=lambda title: (title.revenue is None, -(title.revenue or 0), title.title.lower()))
        self._set_layout_order_from_titles(ordered)
        self.statusBar().showMessage("Sorted by box office where available.")

    def shuffle_layout(self) -> None:
        self._push_undo()
        ids = [title.imdb_title_id for title in self._ordered_active_titles() if title.imdb_title_id]
        random.shuffle(ids)
        self.project.layout_order = ids
        self.project.dirty = True
        self._refresh_all(rebuild=True)
        self.statusBar().showMessage("Shuffled layout.")

    def _set_layout_order_from_titles(self, titles: list[Title]) -> None:
        self.project.layout_order = [title.imdb_title_id for title in titles if title.imdb_title_id]
        self.project.dirty = True
        self._refresh_all(rebuild=True)

    def bench_selected_titles(self) -> None:
        self._bench_titles(self._selected_active_titles())

    def promote_selected_titles(self) -> None:
        titles = self._selected_benched_titles()
        if not titles:
            return
        self._push_undo()
        for title in titles:
            title.benched = False
            title.bench_reason = ""
            if title.imdb_title_id and title.imdb_title_id not in self.project.layout_order:
                self.project.layout_order.append(title.imdb_title_id)
        self.project.dirty = True
        self._refresh_all(rebuild=True)

    def swap_selected_titles(self) -> None:
        active_titles = self._selected_active_titles()
        bench_titles = self._selected_benched_titles()
        if len(active_titles) != 1 or len(bench_titles) != 1:
            return
        self._push_undo()
        active_title = active_titles[0]
        bench_title = bench_titles[0]
        active_title.benched = True
        active_title.bench_reason = "manual"
        bench_title.benched = False
        bench_title.bench_reason = ""
        if active_title.imdb_title_id in self.project.layout_order:
            index = self.project.layout_order.index(active_title.imdb_title_id)
            self.project.layout_order[index] = bench_title.imdb_title_id or ""
        elif bench_title.imdb_title_id:
            self.project.layout_order.append(bench_title.imdb_title_id)
        self.project.layout_order = [item for item in self.project.layout_order if item]
        self.project.dirty = True
        self._refresh_all(rebuild=True)

    def _workspace_poster_swap_requested(self, source_imdb_id: str, target_imdb_id: str) -> None:
        if source_imdb_id not in self.project.layout_order or target_imdb_id not in self.project.layout_order:
            return
        self._push_undo()
        source_index = self.project.layout_order.index(source_imdb_id)
        target_index = self.project.layout_order.index(target_imdb_id)
        self.project.layout_order[source_index], self.project.layout_order[target_index] = (
            self.project.layout_order[target_index],
            self.project.layout_order[source_index],
        )
        self.project.dirty = True
        self._refresh_all(rebuild=True)
        self._workspace_poster_selected(source_imdb_id)

    def _bench_poster_replace_requested(self, bench_imdb_id: str, canvas_imdb_id: str) -> None:
        bench_title = self.project.title_by_imdb_id(bench_imdb_id)
        canvas_title = self.project.title_by_imdb_id(canvas_imdb_id)
        if bench_title is None or canvas_title is None or not bench_title.benched or canvas_title.benched:
            return

        self._push_undo()
        canvas_title.benched = True
        canvas_title.bench_reason = "manual"
        bench_title.benched = False
        bench_title.bench_reason = ""

        if canvas_imdb_id in self.project.layout_order:
            index = self.project.layout_order.index(canvas_imdb_id)
            self.project.layout_order[index] = bench_imdb_id
        elif bench_imdb_id not in self.project.layout_order:
            self.project.layout_order.append(bench_imdb_id)

        self.project.dirty = True
        self._refresh_all(rebuild=True)
        self._workspace_poster_selected(bench_imdb_id)
        self.statusBar().showMessage(f"Replaced {canvas_title.title} with {bench_title.title}.")

    def _canvas_bench_poster_swap_requested(self, canvas_imdb_id: str, bench_imdb_id: str) -> None:
        canvas_title = self.project.title_by_imdb_id(canvas_imdb_id)
        bench_title = self.project.title_by_imdb_id(bench_imdb_id)
        if canvas_title is None or bench_title is None or canvas_title.benched or not bench_title.benched:
            return

        self._push_undo()
        canvas_title.benched = True
        canvas_title.bench_reason = "manual"
        bench_title.benched = False
        bench_title.bench_reason = ""

        if canvas_imdb_id in self.project.layout_order:
            index = self.project.layout_order.index(canvas_imdb_id)
            self.project.layout_order[index] = bench_imdb_id
        elif bench_imdb_id not in self.project.layout_order:
            self.project.layout_order.append(bench_imdb_id)

        self.project.layout_order = [item for item in self.project.layout_order if item]
        self.project.dirty = True
        self._refresh_all(rebuild=True)
        self._workspace_poster_selected(bench_imdb_id)
        self.statusBar().showMessage(f"Swapped {canvas_title.title} with {bench_title.title} on the Bench.")

    def _promote_bench_ids(self, imdb_title_ids: object) -> None:
        ids = [str(item) for item in (imdb_title_ids or []) if item]
        titles = [
            title for title in self.project.benched_titles
            if title.imdb_title_id in ids
        ]
        if not titles:
            return
        self._push_undo()
        for title in titles:
            title.benched = False
            title.bench_reason = ""
            if title.imdb_title_id and title.imdb_title_id not in self.project.layout_order:
                self.project.layout_order.append(title.imdb_title_id)
        self.project.dirty = True
        self._refresh_all(rebuild=True)
        self.workspace.set_selected_posters([title.imdb_title_id for title in titles if title.imdb_title_id])
        self.statusBar().showMessage(f"Promoted {len(titles)} poster{'s' if len(titles) != 1 else ''} from the Bench.")

    def _show_workspace_context_menu(self, imdb_title_ids: object, global_position: object) -> None:
        ids = [str(item) for item in (imdb_title_ids or []) if item]
        titles = [
            title for title in self.project.active_titles
            if title.imdb_title_id in ids
        ]
        if not titles:
            return
        menu = QMenu(self)
        if len(titles) == 1:
            open_imdb_action = menu.addAction("Open on IMDb")
            menu.addSeparator()
        else:
            open_imdb_action = None
        bench_action = menu.addAction("Bench")
        delete_action = menu.addAction("Delete from Project...")
        action = menu.exec(global_position)
        if action == open_imdb_action:
            self._open_title_on_imdb(titles[0])
        elif action == bench_action:
            self._bench_titles(titles)
        elif action == delete_action:
            self.delete_selected_titles(titles)

    def _bench_titles(self, titles: list[Title]) -> None:
        if not titles:
            return
        self._push_undo()
        for title in titles:
            title.benched = True
            title.bench_reason = "manual"
        self._remove_benched_from_layout_order()
        self.project.dirty = True
        self._refresh_all(rebuild=True)


    def _canvas_drag_released(self, imdb_title_ids: object, global_position: object) -> None:
        """Resolve Canvas releases over the Bench without relying on Qt drop negotiation."""
        ids = [str(item) for item in (imdb_title_ids or []) if item]
        if not ids or not isinstance(global_position, QPoint):
            return

        viewport = self.bench_list.viewport()
        local_position = viewport.mapFromGlobal(global_position)
        if not viewport.rect().contains(local_position):
            return

        target_item = self.bench_list.itemAt(local_position)
        target_id = ""
        if target_item is not None:
            target_id = str(target_item.data(Qt.ItemDataRole.UserRole) or "")

        if len(ids) == 1 and target_id:
            self._canvas_bench_poster_swap_requested(ids[0], target_id)
        else:
            self._canvas_posters_benched(ids)

    def _canvas_posters_benched(self, imdb_title_ids: object) -> None:
        ids = {str(item) for item in (imdb_title_ids or []) if item}
        titles = [
            title for title in self.project.active_titles
            if title.imdb_title_id in ids
        ]
        if not titles:
            return

        self._push_undo()
        for title in titles:
            title.benched = True
            title.bench_reason = "manual"
        self._remove_benched_from_layout_order()
        self.project.dirty = True
        self._refresh_all(rebuild=True)
        count = len(titles)
        self.statusBar().showMessage(f"Benched {count} poster{'s' if count != 1 else ''}.")

    def _show_title_list_context_menu(self, position: QPoint) -> None:
        item = self.title_list.itemAt(position)
        if item is not None and not item.isSelected():
            self.title_list.clearSelection()
            self.title_list.setCurrentItem(item)
            item.setSelected(True)

        selected = self._selected_active_titles()
        if not selected:
            return

        menu = QMenu(self)
        select_poster_action = menu.addAction("Select Poster")
        open_imdb_action = menu.addAction("Open on IMDb")
        menu.addSeparator()
        bench_action = menu.addAction("Bench")
        delete_action = menu.addAction("Delete from Project...")

        action = menu.exec(self.title_list.mapToGlobal(position))
        if action == select_poster_action:
            self._select_first_active_title(selected)
        elif action == open_imdb_action:
            self._open_title_on_imdb(selected[0])
        elif action == bench_action:
            self.bench_selected_titles()
        elif action == delete_action:
            self.delete_selected_titles(selected)

    def _show_bench_list_context_menu(self, position: QPoint) -> None:
        item = self.bench_list.itemAt(position)
        if item is not None and not item.isSelected():
            self.bench_list.clearSelection()
            self.bench_list.setCurrentItem(item)
            item.setSelected(True)

        selected = self._selected_benched_titles()
        if not selected:
            return

        menu = QMenu(self)
        open_imdb_action = menu.addAction("Open on IMDb")
        promote_action = menu.addAction("Promote")
        menu.addSeparator()
        delete_action = menu.addAction("Delete from Project...")

        action = menu.exec(self.bench_list.mapToGlobal(position))
        if action == open_imdb_action:
            self._open_title_on_imdb(selected[0])
        elif action == promote_action:
            self.promote_selected_titles()
        elif action == delete_action:
            self.delete_selected_titles(selected)

    def _select_first_active_title(self, titles: list[Title]) -> None:
        if not titles:
            return
        target = titles[0]
        try:
            row = self.project.active_titles.index(target)
        except ValueError:
            return
        self.title_list.setCurrentRow(row)
        self._refresh_properties_panel_for_title(target)

    def _open_title_on_imdb(self, title: Title) -> None:
        url = title.url
        if not url and title.imdb_title_id:
            url = f"https://www.imdb.com/title/{title.imdb_title_id}/"
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _confirm_delete(self, description: str) -> bool:
        if not self.settings.value("confirm_delete", True, type=bool):
            return True

        box = QMessageBox(self)
        box.setWindowTitle("Delete from Project")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(f"Permanently remove {description} from this project?")
        box.setInformativeText("This can be undone with Ctrl+Z until the project is closed.")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        dont_ask = QCheckBox("Do not ask again", box)
        box.setCheckBox(dont_ask)
        accepted = box.exec() == QMessageBox.StandardButton.Yes
        if accepted and dont_ask.isChecked():
            self.settings.setValue("confirm_delete", False)
        return accepted

    def delete_selected_titles(self, titles: list[Title] | None = None) -> None:
        if titles is None:
            titles = self._selected_active_titles()
            if not titles:
                titles = self._selected_benched_titles()
        if not titles:
            return

        count = len(titles)
        description = titles[0].title if count == 1 else f"{count} selected titles"
        if not self._confirm_delete(description):
            return

        self._delete_titles(titles, description)

    def clear_bench(self) -> None:
        titles = list(self.project.benched_titles)
        if not titles:
            return
        description = f"all {len(titles)} titles on the Bench"
        if not self._confirm_delete(description):
            return
        self._delete_titles(titles, description)

    def _delete_titles(self, titles: list[Title], description: str) -> None:
        self._push_undo()
        deleting_ids = {title.imdb_title_id for title in titles if title.imdb_title_id}
        deleting_objects = {id(title) for title in titles}
        self.project.titles = [title for title in self.project.titles if id(title) not in deleting_objects]
        self.project.layout_order = [item for item in self.project.layout_order if item not in deleting_ids]
        self.project.dirty = True
        self._refresh_all(rebuild=True)
        self.statusBar().showMessage(f"Deleted {description}.")

    # ------------------------------------------------------------------
    # Poster loading / variants

    def load_posters(self) -> None:
        active_titles = self.project.active_titles
        if not active_titles:
            self.statusBar().showMessage("Import titles first.")
            return

        for title in self.project.titles:
            title.missing_poster = False

        self.poster_entries.clear()
        self.current_layout = None
        self.visible_imdb_ids.clear()
        self._ensure_layout_order()

        total = len(active_titles)
        self.create_from_imdb_button.setEnabled(False)
        self._set_progress("Loading posters...", 0, total)

        try:
            for index, title in enumerate(active_titles, start=1):
                self._set_progress(f"Loading posters {index} / {total}: {title.title}", index - 1, total)
                QApplication.processEvents()

                if not title.imdb_title_id:
                    title.missing_poster = True
                    continue

                self._ensure_title_metadata(title)
                poster_path = get_poster(title.imdb_title_id, index=title.selected_poster_index, size="w500")
                if poster_path is None:
                    title.missing_poster = True
                    continue
                title.poster_path = poster_path

            self._rebuild_grid_from_project_layout()
            QTimer.singleShot(80, lambda: self.about_overlay.fade_out(1000))
            self._set_progress("Loaded posters.", total, total)
            self._clear_progress()
            self.statusBar().showMessage("Posters loaded.")
        finally:
            self.create_from_imdb_button.setEnabled(True)

    def previous_poster(self) -> None:
        self._change_selected_poster(-1)

    def next_poster(self) -> None:
        self._change_selected_poster(1)

    def _change_selected_poster(self, delta: int) -> None:
        title = self._selected_active_title()
        if title is None or not title.imdb_title_id:
            return
        count = get_poster_candidate_count(title.imdb_title_id)
        if count <= 0:
            return
        new_index = max(0, min(title.selected_poster_index + delta, count - 1))
        if new_index == title.selected_poster_index:
            return

        self._push_undo()
        title.selected_poster_index = new_index
        self.project.dirty = True
        poster_path = get_poster(title.imdb_title_id, index=new_index, size="w500")
        if poster_path is None:
            return
        title.poster_path = poster_path
        self.workspace.update_poster(title.imdb_title_id, poster_path)
        self._replace_poster_entry(title.imdb_title_id, poster_path)
        self._refresh_properties_panel_for_title(title)
        self._update_window_title()

    # ------------------------------------------------------------------
    # Canvas commands

    def choose_canvas_color(self) -> None:
        original = self.project.canvas_color
        dialog = QColorDialog(QColor(original), self)
        dialog.setOption(QColorDialog.ColorDialogOption.NoButtons, False)
        dialog.currentColorChanged.connect(self._canvas_color_preview_changed)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # selectedColor() is the committed value. currentColor() can still
            # report the initial colour on some native Qt colour dialogs.
            color = dialog.selectedColor()
            if color.isValid() and color.name() != original:
                self._push_undo()
                self.project.canvas_color = color.name()
                self.workspace.set_canvas_color(self.project.canvas_color)
                self.project.dirty = True
                self._update_window_title()
        else:
            self.workspace.set_canvas_color(original)

    def _canvas_color_preview_changed(self, color: QColor) -> None:
        if color.isValid():
            self.workspace.set_canvas_color(color)

    def _airiness_changed(self, value: int) -> None:
        if self._updating_canvas_controls:
            return
        self._push_undo()
        # Airiness only changes spacing. It must never promote titles from the Bench.
        self.project.airiness = value
        self.airiness_label.setText(f"Airiness: {value}")
        self.project.dirty = True
        self._refresh_all(rebuild=True)

    def _canvas_preset_changed(self, preset_name: str) -> None:
        if self._updating_canvas_controls or preset_name not in CANVAS_PRESETS:
            return
        if preset_name == "Custom":
            return
        self._push_undo()
        self._promote_auto_benched_titles()
        width, height = CANVAS_PRESETS[preset_name]
        self.project.canvas_preset = preset_name
        self.project.page_width_mm = width
        self.project.page_height_mm = height
        self._sync_canvas_controls_from_project()
        self._apply_canvas_size_change()

    def _manual_canvas_size_changed(self, value: float) -> None:
        if self._updating_canvas_controls:
            return
        self._push_undo()
        self._promote_auto_benched_titles()
        self.project.canvas_preset = "Custom"
        self.project.page_width_mm = self.canvas_width_spin.value()
        self.project.page_height_mm = self.canvas_height_spin.value()
        self._sync_canvas_controls_from_project()
        self._apply_canvas_size_change()

    def _apply_canvas_size_change(self) -> None:
        self.workspace.set_page_size(self.project.page_width_mm, self.project.page_height_mm)
        self.workspace.set_canvas_color(self.project.canvas_color)
        self.project.dirty = True
        self._refresh_all(rebuild=True)

    def _sync_canvas_controls_from_project(self) -> None:
        self._updating_canvas_controls = True
        try:
            preset = self.project.canvas_preset if self.project.canvas_preset in CANVAS_PRESETS else "Custom"
            self.canvas_preset_combo.setCurrentText(preset)
            self.canvas_width_spin.setValue(float(self.project.page_width_mm))
            self.canvas_height_spin.setValue(float(self.project.page_height_mm))
        finally:
            self._updating_canvas_controls = False

    # ------------------------------------------------------------------
    # Rebuild / refresh

    def _refresh_all(self, *, rebuild: bool) -> None:
        self._ensure_layout_order()
        self.workspace.set_canvas_color(self.project.canvas_color)
        if rebuild and any(title.poster_path for title in self.project.titles):
            self._rebuild_grid_from_project_layout()
        self._refresh_project_panel()
        self._refresh_properties_panel()
        self._update_window_title()
        self._update_history_actions()

    def _ensure_layout_order(self) -> None:
        active_ids = self.project.active_imdb_ids()
        active_id_set = set(active_ids)
        self.project.layout_order = [imdb_id for imdb_id in self.project.layout_order if imdb_id in active_id_set]
        for imdb_id in active_ids:
            if imdb_id not in self.project.layout_order:
                self.project.layout_order.append(imdb_id)

    def _remove_benched_from_layout_order(self) -> None:
        active_id_set = set(self.project.active_imdb_ids())
        self.project.layout_order = [imdb_id for imdb_id in self.project.layout_order if imdb_id in active_id_set]

    def _ordered_active_titles(self) -> list[Title]:
        self._ensure_layout_order()
        titles: list[Title] = []
        for imdb_id in self.project.layout_order:
            title = self.project.title_by_imdb_id(imdb_id)
            if title and not title.benched and not title.missing_poster:
                titles.append(title)
        return titles

    def _rebuild_grid_from_project_layout(self) -> None:
        self._ensure_layout_order()
        ordered_titles = self._ordered_active_titles()
        self.poster_entries = [
            (title.imdb_title_id, title.poster_path)
            for title in ordered_titles
            if title.imdb_title_id and title.poster_path
        ]

        if not self.poster_entries:
            self.current_layout = None
            self.visible_imdb_ids = []
            self.workspace.clear_posters()
            return

        layout = calculate_grid_layout(
            len(self.poster_entries),
            self.project.page_width_mm,
            self.project.page_height_mm,
            airiness=self.project.airiness,
        )

        if layout.omitted_count > 0:
            omitted_entries = self.poster_entries[layout.used_count:]
            omitted_ids = {imdb_id for imdb_id, _ in omitted_entries}
            for title in self.project.active_titles:
                if title.imdb_title_id in omitted_ids:
                    title.benched = True
                    title.bench_reason = "layout"
            self._remove_benched_from_layout_order()
            self.poster_entries = self.poster_entries[: layout.used_count]
            layout = calculate_grid_layout(
                len(self.poster_entries),
                self.project.page_width_mm,
                self.project.page_height_mm,
                airiness=self.project.airiness,
            )

        self.current_layout = layout
        self.visible_imdb_ids = [imdb_id for imdb_id, _ in self.poster_entries[: layout.used_count]]
        self.workspace.show_poster_grid(self.poster_entries, layout)
        self._refresh_project_panel()

    def _promote_auto_benched_titles(self) -> None:
        for title in self.project.titles:
            if title.benched and title.bench_reason == "layout":
                title.benched = False
                title.bench_reason = ""
                if title.imdb_title_id and title.imdb_title_id not in self.project.layout_order:
                    self.project.layout_order.append(title.imdb_title_id)

    def _replace_poster_entry(self, imdb_title_id: str, poster_path: Path) -> None:
        self.poster_entries = [
            (entry_id, poster_path if entry_id == imdb_title_id else entry_path)
            for entry_id, entry_path in self.poster_entries
        ]

    # ------------------------------------------------------------------
    # Metadata / save-load

    def _ensure_metadata_for_titles(self, titles: list[Title], label: str) -> None:
        total = len(titles)
        if total <= 0:
            return
        for index, title in enumerate(titles, start=1):
            self._set_progress(f"{label} {index} / {total}: {title.title}", index - 1, total)
            QApplication.processEvents()
            self._ensure_title_metadata(title)
        self._set_progress(f"{label} complete.", total, total)
        self._clear_progress()

    def _ensure_title_metadata(self, title: Title) -> None:
        if not title.imdb_title_id:
            return
        metadata = lookup_imdb_id(title.imdb_title_id)
        if metadata is None:
            return
        if metadata.year is not None:
            title.year = metadata.year
        if getattr(metadata, "revenue", None) is not None:
            title.revenue = metadata.revenue
        if getattr(metadata, "popularity", None) is not None:
            title.popularity = metadata.popularity

    def _save_project_file(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "name": self.project.name,
            "source": self.project.source,
            "canvas_color": self.project.canvas_color,
            "airiness": self.project.airiness,
            "page_width_mm": self.project.page_width_mm,
            "page_height_mm": self.project.page_height_mm,
            "canvas_preset": self.project.canvas_preset,
            "layout_order": self.project.layout_order,
            "titles": [
                {
                    "title": title.title,
                    "year": title.year,
                    "imdb_title_id": title.imdb_title_id,
                    "url": title.url,
                    "selected_poster_index": title.selected_poster_index,
                    "benched": title.benched,
                    "bench_reason": title.bench_reason,
                    "missing_poster": title.missing_poster,
                    "revenue": title.revenue,
                    "popularity": title.popularity,
                }
                for title in self.project.titles
            ],
        }
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
        self.project.path = path
        self._remember_project_directory(path.parent)
        self.project.dirty = False
        self.statusBar().showMessage(f"Saved {path.name}")
        self._update_window_title()

    def _load_project_file(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as file:
            data: dict[str, Any] = json.load(file)

        titles = [
            Title(
                title=str(raw.get("title", "")).strip(),
                year=raw.get("year"),
                imdb_title_id=raw.get("imdb_title_id"),
                url=raw.get("url"),
                selected_poster_index=int(raw.get("selected_poster_index", 0)),
                benched=bool(raw.get("benched", False)),
                bench_reason=str(raw.get("bench_reason") or ("manual" if bool(raw.get("benched", False)) else "")),
                missing_poster=bool(raw.get("missing_poster", False)),
                revenue=raw.get("revenue"),
                popularity=raw.get("popularity"),
            )
            for raw in data.get("titles", [])
        ]

        self.project = Project(
            name=str(data.get("name") or "Untitled Project"),
            path=path,
            source=str(data.get("source") or "None"),
            titles=titles,
            dirty=False,
            canvas_color=str(data.get("canvas_color") or "#000000"),
            airiness=int(data.get("airiness", 50)),
            page_width_mm=float(data.get("page_width_mm", DEFAULT_PAGE_WIDTH_MM)),
            page_height_mm=float(data.get("page_height_mm", DEFAULT_PAGE_HEIGHT_MM)),
            canvas_preset=str(data.get("canvas_preset") or "Custom"),
            layout_order=[str(item) for item in data.get("layout_order", [])],
        )

        self.undo_stack.clear()
        self.redo_stack.clear()
        self.poster_entries.clear()
        self.current_layout = None
        self.visible_imdb_ids.clear()
        self.workspace.clear_posters()
        self.workspace.set_page_size(self.project.page_width_mm, self.project.page_height_mm)
        self.workspace.set_canvas_color(self.project.canvas_color)
        self.airiness_slider.setValue(self.project.airiness)
        self._sync_canvas_controls_from_project()
        self._refresh_all(rebuild=False)
        self.load_posters()
        self.statusBar().showMessage(f"Opened {path.name}")

    # ------------------------------------------------------------------
    # Properties / selection

    def _refresh_project_panel(self) -> None:
        active_titles = self.project.active_titles
        benched_titles = self.project.benched_titles

        self.title_list.clear()
        if not active_titles:
            empty = QListWidgetItem("(empty)")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            empty.setSizeHint(QSize(0, 18))
            self.title_list.addItem(empty)
        else:
            for title in active_titles:
                item = QListWidgetItem(self._title_label(title))
                item.setToolTip(self._title_tooltip(title))
                item.setData(Qt.ItemDataRole.UserRole, title.imdb_title_id or "")
                item.setSizeHint(QSize(0, 18))
                if title.missing_poster:
                    item.setForeground(QBrush(QColor("#ffb0a8")))
                self.title_list.addItem(item)

        selected_bench_ids = {
            str(item.data(Qt.ItemDataRole.UserRole) or "")
            for item in self.bench_list.selectedItems()
        }
        self.bench_list.clear()
        for title in benched_titles:
            item = QListWidgetItem()
            # Give every Bench item its final cell geometry before insertion.
            # Without an explicit size hint, Qt can perform the first icon-mode
            # paint using a temporarily collapsed row rectangle, clipping the
            # poster to a narrow strip until a later refresh triggers reflow.
            item.setSizeHint(self.bench_list.gridSize())
            item.setToolTip(self._title_tooltip(title))
            item.setData(Qt.ItemDataRole.UserRole, title.imdb_title_id or "")
            pixmap = QPixmap(str(title.poster_path)) if title.poster_path else QPixmap()
            if not pixmap.isNull():
                item.setIcon(QIcon(pixmap))
            else:
                item.setText(self._title_label(title))
            self.bench_list.addItem(item)
            if title.imdb_title_id in selected_bench_ids:
                item.setSelected(True)
        self.bench_list.doItemsLayout()
        self.bench_list.viewport().update()
        # ResizeMode.Adjust may need one event-loop turn after a clear/repopulate
        # before the viewport has its final dimensions. Re-run layout once then
        # so the first Bench population is painted at full poster height.
        QTimer.singleShot(0, self.bench_list.doItemsLayout)
        QTimer.singleShot(0, self.bench_list.viewport().update)

        self.clear_bench_button.setEnabled(bool(benched_titles))

        missing_count = sum(1 for title in self.project.titles if title.missing_poster)
        self.project_summary_label.setText(
            f"Imported: {len(self.project.titles)}   "
            f"Visible: {len(self.visible_imdb_ids)}   "
            f"Benched: {len(benched_titles)}   "
            f"Missing: {missing_count}"
        )
        self._update_swap_button_state()

    def _refresh_properties_panel(self) -> None:
        title = self._selected_active_title()
        if title is None:
            self.poster_preview_label.clear()
            self.poster_counter_label.setText("Poster")
            self.previous_poster_button.setEnabled(False)
            self.next_poster_button.setEnabled(False)
            self.workspace.select_poster(None)
            return
        self._refresh_properties_panel_for_title(title)

    def _refresh_properties_panel_for_title(self, title: Title, *, sync_workspace: bool = True) -> None:
        if not title.imdb_title_id:
            self.poster_preview_label.clear()
            self.poster_counter_label.setText("Poster")
            self.previous_poster_button.setEnabled(False)
            self.next_poster_button.setEnabled(False)
            if sync_workspace:
                self.workspace.select_poster(None)
            return

        count = get_poster_candidate_count(title.imdb_title_id)
        if count <= 0:
            self.poster_preview_label.clear()
            self.poster_counter_label.setText("Poster")
            self.previous_poster_button.setEnabled(False)
            self.next_poster_button.setEnabled(False)
            if sync_workspace:
                self.workspace.select_poster(title.imdb_title_id)
            return

        title.selected_poster_index = max(0, min(title.selected_poster_index, count - 1))
        if count == 1:
            self.poster_counter_label.setText("Poster")
        else:
            self.poster_counter_label.setText(f"Poster {title.selected_poster_index + 1} of {count}")
        self.previous_poster_button.setEnabled(count > 1 and title.selected_poster_index > 0)
        self.next_poster_button.setEnabled(count > 1 and title.selected_poster_index < count - 1)

        poster_path = get_poster(title.imdb_title_id, index=title.selected_poster_index, size="w500")
        if poster_path is None:
            self.poster_preview_label.clear()
            return
        title.poster_path = poster_path
        self._set_poster_preview(poster_path)
        if sync_workspace:
            self.workspace.select_poster(title.imdb_title_id)
        prefetch_poster_neighbors(
            title.imdb_title_id,
            index=title.selected_poster_index,
            radius=2,
            size="w500",
        )

    def _set_poster_preview(self, poster_path: Path) -> None:
        pixmap = QPixmap(str(poster_path))
        if pixmap.isNull():
            self.poster_preview_label.clear()
            return
        available_width = max(1, self.poster_preview_label.contentsRect().width() - 8)
        available_height = max(1, self.poster_preview_label.contentsRect().height() - 8)
        scaled = pixmap.scaled(
            available_width,
            available_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.poster_preview_label.setPixmap(scaled)

    def _title_selection_changed(self, current, previous) -> None:
        self.bench_list.clearSelection()
        self._refresh_properties_panel()
        title = self._selected_active_title()
        if len(self.workspace.selected_poster_ids()) <= 1:
            self.workspace.select_poster(title.imdb_title_id if title and title.imdb_title_id else None)

    def _workspace_poster_selected(self, imdb_title_id: str) -> None:
        for row, title in enumerate(self.project.active_titles):
            if title.imdb_title_id == imdb_title_id:
                # Updating the hidden title list normally emits
                # currentItemChanged. Its handler refreshes the properties panel
                # and synchronises the workspace to one poster, which collapses
                # a Ctrl-selected Canvas set. Keep this Canvas-originated update
                # silent and refresh only the preview.
                self.title_list.blockSignals(True)
                try:
                    self.title_list.setCurrentRow(row)
                finally:
                    self.title_list.blockSignals(False)
                self.bench_list.clearSelection()
                self._refresh_properties_panel_for_title(title, sync_workspace=False)
                return

    def _workspace_selection_changed(self, imdb_title_ids: list[str]) -> None:
        selected_ids = set(imdb_title_ids)
        self.title_list.blockSignals(True)
        try:
            self.title_list.clearSelection()
            for row, title in enumerate(self.project.active_titles):
                if title.imdb_title_id in selected_ids:
                    item = self.title_list.item(row)
                    if item is not None:
                        item.setSelected(True)
        finally:
            self.title_list.blockSignals(False)
        self.bench_list.clearSelection()
        self._update_swap_button_state()

    def _selected_active_title(self) -> Title | None:
        row = self.title_list.currentRow()
        active_titles = self.project.active_titles
        if row < 0 or row >= len(active_titles):
            return None
        return active_titles[row]

    def _selected_active_titles(self) -> list[Title]:
        selected_ids = set(self.workspace.selected_poster_ids())
        if selected_ids:
            return [title for title in self.project.active_titles if title.imdb_title_id in selected_ids]
        active_titles = self.project.active_titles
        rows = sorted({self.title_list.row(item) for item in self.title_list.selectedItems()})
        return [active_titles[row] for row in rows if 0 <= row < len(active_titles)]

    def _selected_benched_titles(self) -> list[Title]:
        selected_ids = {
            str(item.data(Qt.ItemDataRole.UserRole) or "")
            for item in self.bench_list.selectedItems()
        }
        if not selected_ids:
            return []
        return [
            title for title in self.project.benched_titles
            if title.imdb_title_id in selected_ids
        ]

    def _update_swap_button_state(self) -> None:
        self.swap_selected_button.setEnabled(
            len(self._selected_active_titles()) == 1 and len(self._selected_benched_titles()) == 1
        )

    def _title_label(self, title: Title) -> str:
        label = title.title
        if title.year is not None:
            label += f" ({title.year})"
        return label

    def _title_tooltip(self, title: Title) -> str:
        label = self._title_label(title)
        if title.missing_poster:
            label += "\nMissing poster on TMDb"
        if title.benched and title.bench_reason == "layout":
            label += "\nAutomatically benched by layout"
        return label

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        selected_title = self._selected_active_title()
        if selected_title is not None and selected_title.poster_path is not None:
            self._set_poster_preview(selected_title.poster_path)
        if hasattr(self, "about_overlay"):
            self.about_overlay.reposition()
        if hasattr(self, "progress_popup"):
            x = max(12, (self.workspace.viewport().width() - self.progress_popup.width()) // 2)
            self.progress_popup.move(x, 18)
            self.progress_popup.raise_()

    # ------------------------------------------------------------------
    # Progress / title bar

    def _set_progress(self, text: str, value: int, maximum: int) -> None:
        self.progress_label.setText(text)
        self.progress_bar.setMaximum(max(1, maximum))
        self.progress_bar.setValue(max(0, min(value, maximum)))
        self._set_progress_active(True)

    def _clear_progress(self) -> None:
        self.progress_label.setText("")
        self.progress_bar.setValue(0)
        self._set_progress_active(False)

    def _set_progress_active(self, active: bool) -> None:
        self.progress_label.setProperty("active", active)
        self.progress_bar.setProperty("active", active)
        for widget in (self.progress_label, self.progress_bar):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()
        if hasattr(self, "progress_popup"):
            self.progress_popup.setVisible(active)
            if active:
                x = max(12, (self.workspace.viewport().width() - self.progress_popup.width()) // 2)
                self.progress_popup.adjustSize()
                self.progress_popup.setFixedWidth(390)
                self.progress_popup.move(x, 18)
                self.progress_popup.raise_()

    def _update_window_title(self) -> None:
        name = self.project.name or "Untitled Project"
        source = self.project.source
        dirty = " *" if self.project.dirty else ""
        if source and source != "None":
            self.setWindowTitle(f"Posterfolio — {name} — {source}{dirty}")
        else:
            self.setWindowTitle(f"Posterfolio — {name}{dirty}")
