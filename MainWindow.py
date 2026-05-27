"""
MainWindow.py

Reorganized + commented version of your current MainWindow.

Main ideas:
- Keep _build_ui() readable by splitting it into small “section builders”
- Keep all signal connections in ONE place (_connect_signals)
- Keep “UI -> Model” updates in clearly named handlers
- Use the resize debounce timer you added (good!)

Notes:
- I preserved your existing behavior and variable names as much as possible.
- I removed one duplicated “Line Width” block you accidentally had twice in your original code.
- I kept your existing controller API calls unchanged.
"""

import json
import os
from ast import literal_eval
from functools import partial
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QLabel, QListWidget, QListWidgetItem, QLineEdit, QComboBox,
    QFileDialog, QMessageBox, QHBoxLayout, QVBoxLayout, QGridLayout, QSlider, QCheckBox, QScrollArea, QApplication, QDialog, QAbstractButton, QShortcut, QStackedWidget, QSplitter,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence

from PlotCanvas import PlotCanvas
from AppController import AppController
from Color_modules import (
    PLOTLY_PALETTES,
    populate_color_combo,
    selected_color,
    ensure_color_in_combo,
)
from DataFile import load_data_file
from AdvancedDialog import AdvancedDialog
from PlotterControlPanel import PlotterControlPanel
from StartupLandingPage import StartupLandingPage
from plot_modes import (
    friendly_3d_style,
    friendly_plot_mode,
    PLOT_MODE_OPTIONS,
    plot_mode_requires_z,
    plot_mode_supports_render_style,
    plot_mode_supports_direct_color,
    plot_mode_supports_secondary_axis,
    plot_mode_supports_z_ticks,
    render_style_uses_colormap,
)
from state_store import StateStore
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

class MainWindow(QMainWindow):
    def __init__(self, initial_plot_mode=None, prompt_for_mode=True):
        super().__init__()
        self.setWindowTitle("Clean PyQt Plotter")
        self.resize(1440, 900)

        self.canvas = PlotCanvas()
        self.controller = AppController(self.canvas)
        self.state_store = StateStore()
        self._undo_stack = []
        self._redo_stack = []
        self._restoring_state = False
        self._dirty = False
        self._current_project_path = None
        self._history_limit = 50

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.controller.update_plot)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._write_autosave)

        self._active_subplot = None
        self._startup_cancelled = False
        self._build_ui()
        self._connect_signals()
        self._bind_shortcuts()
        self._refresh_recent_projects()
        self._update_history_actions()
        self._maybe_restore_autosave()
        self._initialize_plot_mode(initial_plot_mode, prompt_for_mode)

    # ------------------------------------------------------------------
    # Qt events
    # ------------------------------------------------------------------
    def resizeEvent(self, event):
        """
        Qt fires many resize events while the user is resizing / toggling fullscreen.
        Debounce redraw so we repaint only once after the resizing stops.
        """
        super().resizeEvent(event)

        # Mark plot as needing layout update (your PlotConfig uses .dirty)
        self.controller.config.dirty = True

        # Restart timer on each resize event
        self._resize_timer.start(150)

    def closeEvent(self, event):
        if self._is_headless():
            event.accept()
            return
        self._write_autosave()
        if not self._dirty:
            event.accept()
            return

        reply = QMessageBox.question(
            self,
            "Unsaved changes",
            "Save changes before closing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if reply == QMessageBox.Cancel:
            event.ignore()
            return
        if reply == QMessageBox.Save:
            if not self.save_project():
                event.ignore()
                return
        event.accept()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view_stack = QStackedWidget()
        layout.addWidget(self.view_stack)

        self.landing_page = StartupLandingPage(self._startup_mode_cards())
        self.landing_page.modeActivated.connect(self._activate_plot_mode)
        self.view_stack.addWidget(self.landing_page)

        self.workspace_page = self._build_workspace_page()
        self.view_stack.addWidget(self.workspace_page)

        self._show_landing_page()

    def _build_workspace_page(self):
        workspace = QWidget()
        self.main_layout = QVBoxLayout(workspace)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.workspace_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.workspace_splitter)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setMinimumWidth(280)
        self.controls = PlotterControlPanel(self.controller)
        scroll_area.setWidget(self.controls)
        self.workspace_splitter.addWidget(scroll_area)

        # Right: toolbar + canvas stacked vertically
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.workspace_splitter.addWidget(right_panel)
        self.workspace_splitter.setChildrenCollapsible(False)
        self.workspace_splitter.setStretchFactor(0, 0)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setSizes([380, 1060])

        # Store for later use
        self._right_layout = right_layout



        # Build control sections (top → bottom)
        self._bind_control_attrs()

        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self._right_layout.addWidget(self.toolbar, 0)
        self._right_layout.addWidget(self.canvas, 1)

        self._mpl_label_sync_guard = False
        self._skip_next_draw_event = False
        # Call sync only when a toolbar action is used
        for act in self.toolbar.actions():
            act.triggered.connect(lambda checked=False, a=act: self._on_toolbar_action(a))
        return workspace

    def _startup_mode_cards(self):
        preview_root = Path(__file__).resolve().parent / "assets" / "plot_previews"
        cards = {
            "line2d": {
                "button_label": "2D line plot",
                "title": "2D line plots for curves and comparisons",
                "description": (
                    "Use this when you want classic X/Y plotting with one or more curves, "
                    "subplot layouts, and optional secondary Y axes."
                ),
                "image": preview_root / "line2d_preview.png",
            },
            "heatmap2d": {
                "button_label": "2D heatmap",
                "title": "2D heatmaps for value fields",
                "description": (
                    "Best for X/Y/Z point data where Z is shown by color. "
                    "This mode gives you a color-mapped view with a matching colorbar."
                ),
                "image": preview_root / "heatmap2d_preview.png",
            },
            "plot3d": {
                "button_label": "3D plot",
                "title": "3D lines, surfaces, and density volumes",
                "description": (
                    "Choose this to work with X/Y/Z data in three dimensions. "
                    "You can build line plots, surfaces, and density-style volume views."
                ),
                "image": preview_root / "plot3d_preview.png",
            },
        }
        return cards

    def _show_landing_page(self):
        self.view_stack.setCurrentWidget(self.landing_page)

    def _show_workspace(self):
        self.view_stack.setCurrentWidget(self.workspace_page)

    def _bind_control_attrs(self):
        attr_names = [
            "control_layout",
            "add_file_btn",
            "remove_file_btn",
            "files_list",
            "file_preview",
            "plot_mode_value",
            "dimension_combo",
            "subplot_label",
            "subplot_list",
            "x_ticks_edit",
            "y_ticks_edit",
            "z_ticks_label",
            "z_ticks_edit",
            "add_curve_btn",
            "curve_list",
            "remove_curve_btn",
            "curve_name_edit",
            "x_combo",
            "y_combo",
            "z_combo",
            "x_column_label",
            "y_column_label",
            "z_column_label",
            "axis_combo",
            "axis_label",
            "subplot_index_combo",
            "subplot_index_label",
            "render_style_label",
            "render_style_combo",
            "palette_combo",
            "palette_label",
            "color_combo",
            "color_label",
            "color_mode_combo",
            "color_mode_label",
            "show_colorbar_checkbox",
            "colorbar_label",
            "colorbar_label_edit",
            "opacity_slider",
            "undo_btn",
            "redo_btn",
            "export_png_btn",
            "export_svg_btn",
            "export_pdf_btn",
            "advanced_btn",
            "plot_btn",
            "save_project_btn",
            "open_project_btn",
            "recent_projects_combo",
            "open_recent_btn",
        ]
        for name in attr_names:
            setattr(self, name, getattr(self.controls, name))

    def _on_toolbar_action(self, action):
        txt = (action.text() or "").strip()
        if txt == "Customize":
            # Let MPL create the dialog, then hook its buttons
            QTimer.singleShot(0, self._hook_customize_dialog)

    def _hook_customize_dialog(self):
        # Find the top-level dialog Matplotlib just opened
        dlg = None
        for w in QApplication.topLevelWidgets():
            if isinstance(w, QDialog):
                title = (w.windowTitle() or "").lower()
                # Matplotlib titles vary by version; these catch the common ones
                if "customize" in title or "figure options" in title or "edit" in title:
                    dlg = w
                    break

        if dlg is None:
            return

        # Connect Apply/OK buttons
        for b in dlg.findChildren(QAbstractButton):
            t = (b.text() or "").strip().lower()
            if t in ("apply", "&apply", "ok", "&ok"):
                b.clicked.connect(self._sync_labels_from_mpl)
                print("Connected customize dialog button:", t)

        # (optional) if you want sync on close too:
        # dlg.finished.connect(self._sync_from_mpl_and_update_curve_list)


    # -------------------------
    # Sections
    # -------------------------
    def _build_files_section(self):
        """Buttons + list of loaded files."""
        self.add_file_btn = QPushButton("Add file")
        self.remove_file_btn = QPushButton("Remove Selected file")

        self.control_layout.addWidget(self.add_file_btn)
        self.control_layout.addWidget(self.remove_file_btn)

        self.control_layout.addWidget(QLabel("Files"))
        self.files_list = QListWidget()
        self.control_layout.addWidget(self.files_list)

    def _build_axis_labels_section(self):
        """X/Y axis label edits (two columns)."""
        grid = QGridLayout()

        # Row 0: label headers
        grid.addWidget(QLabel("X label"), 0, 0)
        grid.addWidget(QLabel("Y label"), 0, 1)

        # Row 1: line edits
        self.xlabel_edit = QLineEdit()
        self.ylabel_edit = QLineEdit()
        self.xlabel_edit.setPlaceholderText("X label")
        self.ylabel_edit.setPlaceholderText("Y label")

        grid.addWidget(self.xlabel_edit, 1, 0)
        grid.addWidget(self.ylabel_edit, 1, 1)

        self.control_layout.addLayout(grid)

    def _build_dimension_section(self):
        """Canvas aspect ratio selection (e.g., (4,3))."""
        self.control_layout.addWidget(QLabel("Dimension"))

        self.dimension_combo = QComboBox()
        self.dimension_combo.addItems([
            "(1,1)", "(1,2)", "(3,4)", "(5,8)",
            "(2,1)", "(4,3)", "(8,5)"
        ])
        self.control_layout.addWidget(self.dimension_combo)

    def _build_curves_section(self):
        """Curve list + curve settings (name, x/y, axis)."""
        self.add_curve_btn = QPushButton("Add Curve")
        self.control_layout.addWidget(self.add_curve_btn)

        self.control_layout.addWidget(QLabel("Curves"))
        self.curve_list = QListWidget()
        self.control_layout.addWidget(self.curve_list)

        self.remove_curve_btn = QPushButton("Remove Selected Curve")
        self.control_layout.addWidget(self.remove_curve_btn)

        self.control_layout.addWidget(QLabel("Curve name"))
        self.curve_name_edit = QLineEdit()
        self.control_layout.addWidget(self.curve_name_edit)

        xy_layout = QHBoxLayout()
        # X column
        x_layout = QVBoxLayout()
        x_layout.addWidget(QLabel("X column"))
        self.x_combo = QComboBox()
        x_layout.addWidget(self.x_combo)

        # Y column
        y_layout = QVBoxLayout()
        y_layout.addWidget(QLabel("Y column"))
        self.y_combo = QComboBox()
        y_layout.addWidget(self.y_combo)

        xy_layout.addLayout(x_layout)
        xy_layout.addLayout(y_layout)

        self.control_layout.addLayout(xy_layout)

        axis_subplot_layout = QHBoxLayout()

        axis_layout =  QVBoxLayout()
        axis_layout.addWidget(QLabel("Axis"))
        axis_subplot_layout.addLayout(axis_layout)
        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["primary", "secondary"])
        axis_layout.addWidget(self.axis_combo)

        subplot_layout = QVBoxLayout()
        subplot_layout.addWidget(QLabel("Subplot index"))
        axis_subplot_layout.addLayout(subplot_layout)
        self.subplot_index_combo = QComboBox()
        self.subplot_index_combo.addItems(["0"])
        subplot_layout.addWidget(self.subplot_index_combo)

        self.control_layout.addLayout(axis_subplot_layout)


    def _build_color_section(self):
        """Palette selection + swatch combo for curve color."""
        grid = QGridLayout()

        # Labels
        grid.addWidget(QLabel("Color palette"), 0, 0)
        grid.addWidget(QLabel("Curve color"), 0, 1)

        # Palette combo
        self.palette_combo = QComboBox()
        self.palette_combo.addItems(PLOTLY_PALETTES.keys())
        self.palette_combo.setCurrentText(self.controller.config.palette_name)
        grid.addWidget(self.palette_combo, 1, 0)

        # Color swatch combo
        self.color_combo = QComboBox()
        populate_color_combo(self.color_combo, PLOTLY_PALETTES[self.controller.config.palette_name])
        self.color_combo.setFixedWidth(100)
        grid.addWidget(self.color_combo, 1, 1)

        self.control_layout.addLayout(grid)

    def _build_marker_section(self):
        """Marker style + marker size slider."""
        grid = QGridLayout()

        grid.addWidget(QLabel("Markers"), 0, 0)
        grid.addWidget(QLabel("Size"), 0, 1)

        self.marker_combo = QComboBox()
        self.marker_combo.addItems(["None", "o", "s", "^", "D"])
        grid.addWidget(self.marker_combo, 1, 0)

        self.marker_size_combo = QSlider(Qt.Horizontal)
        self.marker_size_combo.setRange(2, 15)
        self.marker_size_combo.setValue(5)
        grid.addWidget(self.marker_size_combo, 1, 1)

        self.control_layout.addLayout(grid)

    def _build_line_section(self):
        """Line style + line width."""
        grid = QGridLayout()

        grid.addWidget(QLabel("Line Style"), 0, 0)
        grid.addWidget(QLabel("Line Width"), 0, 1)

        self.linestyle_combo = QComboBox()
        self.linestyle_combo.addItems(["-", "--", "-.", ":"])
        grid.addWidget(self.linestyle_combo, 1, 0)

        self.linewidth_combo = QComboBox()
        self.linewidth_combo.addItems(["1", "2", "3", "4", "5"])
        # Important: set a value that actually exists in the combo
        self.linewidth_combo.setCurrentText("2")
        grid.addWidget(self.linewidth_combo, 1, 1)

        self.control_layout.addLayout(grid)

    def _build_subplots_section(self):
        self.subplot_label = QLabel("Subplots")
        self.control_layout.addWidget(self.subplot_label)
        self.subplot_list = QListWidget()
        self.control_layout.addWidget(self.subplot_list)
        self.subplot_label.setVisible(False)
        self.subplot_list.setVisible(False)

    def _build_axis_limits_section(self):
        """X/Y axis limits (min/max) with centered text."""
        grid = QGridLayout()

        # --- X limits ---
        grid.addWidget(QLabel("X Limits", alignment=Qt.AlignCenter), 0, 0, 1, 2)
        self.x_min_edit = QLineEdit()
        self.x_max_edit = QLineEdit()
        self._setup_limit_edit(self.x_min_edit, "Min")
        self._setup_limit_edit(self.x_max_edit, "Max")
        grid.addWidget(self.x_min_edit, 1, 0)
        grid.addWidget(self.x_max_edit, 1, 1)

        # --- Y limits ---
        grid.addWidget(QLabel("Y Limits", alignment=Qt.AlignCenter), 0, 2, 1, 2)
        self.y_min_edit = QLineEdit()
        self.y_max_edit = QLineEdit()
        self._setup_limit_edit(self.y_min_edit, "Min")
        self._setup_limit_edit(self.y_max_edit, "Max")
        grid.addWidget(self.y_min_edit, 1, 2)
        grid.addWidget(self.y_max_edit, 1, 3)

        self.control_layout.addLayout(grid)

    def _build_ticks_section(self):
        """X/Y axis ticks number."""
        grid = QGridLayout()

        # --- X ticks ---
        grid.addWidget(QLabel("X Ticks", alignment=Qt.AlignCenter), 0, 0)
        self.x_ticks_edit = QSlider(Qt.Horizontal)
        self.x_ticks_edit.setRange(1, 20)
        self.x_ticks_edit.setValue(5)
        grid.addWidget(self.x_ticks_edit, 1, 0)

        # --- Y ticks ---
        grid.addWidget(QLabel("Y Ticks", alignment=Qt.AlignCenter), 0, 1)
        self.y_ticks_edit = QSlider(Qt.Horizontal)
        self.y_ticks_edit.setRange(1, 20)
        self.y_ticks_edit.setValue(5)
        grid.addWidget(self.y_ticks_edit, 1, 1)

        # grid.addWidget(QLabel("Minor ticks"), 2, 0)
        # self.minor_ticks_checkbox = QCheckBox()
        # grid.addWidget(self.minor_ticks_checkbox, 2, 1)


        self.control_layout.addLayout(grid)

    def _build_grid_section(self):
        """Grid options (major + minor)."""
        grid = QGridLayout()

        grid.addWidget(QLabel("Major Grid"), 0, 0)
        self.major_grid_checkbox = QCheckBox()
        self.major_grid_checkbox.setChecked(True)
        grid.addWidget(self.major_grid_checkbox, 0, 1)

        # grid.addWidget(QLabel("Minor Grid"), 1, 0)
        # self.minor_grid_checkbox = QCheckBox()
        # grid.addWidget(self.minor_grid_checkbox, 1, 1)

        self.control_layout.addLayout(grid)

    def _build_actions_section(self):

        self.advanced_btn = QPushButton("Advanced…")
        self.control_layout.addWidget(self.advanced_btn)

        """Manual plot update button (optional, since most settings update live)."""
        self.plot_btn = QPushButton("Update Plot")
        self.control_layout.addWidget(self.plot_btn)

        self.save_project_btn = QPushButton("Save plot project…")
        self.open_project_btn = QPushButton("Open plot project…")
        self.control_layout.addWidget(self.save_project_btn)
        self.control_layout.addWidget(self.open_project_btn)

        self.save_project_btn.clicked.connect(self.save_project)
        self.open_project_btn.clicked.connect(self.open_project)



    # ------------------------------------------------------------------
    # Small UI helpers
    # ------------------------------------------------------------------
    def _setup_limit_edit(self, edit: QLineEdit, placeholder: str):
        """Common styling for min/max line edits."""
        edit.setPlaceholderText(placeholder)
        edit.setAlignment(Qt.AlignCenter)

    # ------------------------------------------------------------------
    # Signal wiring (all in one place)
    # ------------------------------------------------------------------
    def _connect_signals(self):
        self.add_file_btn.clicked.connect(self.load_file)
        self.remove_file_btn.clicked.connect(self.remove_selected_file)
        self.files_list.currentRowChanged.connect(self.on_file_selected)

        self.subplot_list.currentRowChanged.connect(self.on_subplot_selected)

        self.add_curve_btn.clicked.connect(self.add_curve)
        self.remove_curve_btn.clicked.connect(self.remove_selected_curve)
        self.curve_list.currentRowChanged.connect(self.on_curve_selected)
        self.curve_list.model().rowsMoved.connect(self.on_curve_rows_reordered_from_list)
        self.subplot_index_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.palette_combo.currentTextChanged.connect(self.on_palette_changed)
        self.x_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.y_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.z_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.render_style_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.render_style_combo.currentTextChanged.connect(lambda *_: self._apply_plot_mode_ui())
        self.axis_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.curve_name_edit.editingFinished.connect(self.on_curve_settings_changed)
        self.color_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.color_mode_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.color_mode_combo.currentTextChanged.connect(lambda *_: self._apply_plot_mode_ui())
        self.show_colorbar_checkbox.clicked.connect(self.on_curve_settings_changed)
        self.colorbar_label_edit.editingFinished.connect(self.on_curve_settings_changed)
        self.opacity_slider.valueChanged.connect(self.on_curve_settings_changed)
        self.dimension_combo.currentTextChanged.connect(self.on_canvas_settings_changed)
        self.x_ticks_edit.valueChanged.connect(self.on_canvas_settings_changed)
        self.y_ticks_edit.valueChanged.connect(self.on_canvas_settings_changed)
        self.z_ticks_edit.valueChanged.connect(self.on_canvas_settings_changed)
        self.advanced_btn.clicked.connect(self.open_advanced_dialog)
        self.plot_btn.clicked.connect(self.controller.update_plot)
        self.save_project_btn.clicked.connect(self.save_project)
        self.open_project_btn.clicked.connect(self.open_project)
        self.undo_btn.clicked.connect(self.undo)
        self.redo_btn.clicked.connect(self.redo)
        self.export_png_btn.clicked.connect(partial(self.export_plot, "png"))
        self.export_svg_btn.clicked.connect(partial(self.export_plot, "svg"))
        self.export_pdf_btn.clicked.connect(partial(self.export_plot, "pdf"))
        self.open_recent_btn.clicked.connect(self.open_recent_project)

    def _bind_shortcuts(self):
        standard_shortcuts = [
            QKeySequence.Undo,
            QKeySequence.Redo,
        ]
        for key in standard_shortcuts:
            action = self.undo if key == QKeySequence.Undo else self.redo
            QShortcut(QKeySequence(key), self, activated=action)

        # Keep common Windows/Linux redo bindings available alongside the
        # platform-native sequences that Qt maps on macOS.
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, activated=self.redo)
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self.redo)

    def _snapshot_state(self):
        return json.loads(json.dumps(self.controller.to_dict()))

    def _finalize_state_change(self, before_state, *, mark_dirty=True):
        if self._restoring_state:
            return
        after_state = self._snapshot_state()
        if after_state == before_state:
            return
        self._undo_stack.append(before_state)
        if len(self._undo_stack) > self._history_limit:
            self._undo_stack = self._undo_stack[-self._history_limit:]
        self._redo_stack.clear()
        if mark_dirty:
            self._set_dirty(True)
        self._update_history_actions()

    def _perform_state_change(self, mutator, *, mark_dirty=True):
        before_state = self._snapshot_state()
        result = mutator()
        self._finalize_state_change(before_state, mark_dirty=mark_dirty)
        return result

    def _set_dirty(self, value: bool):
        self._dirty = value
        title = "Clean PyQt Plotter"
        if self._current_project_path:
            title += f" - {Path(self._current_project_path).name}"
        if self._dirty:
            title += " *"
            self._autosave_timer.start(800)
        else:
            self._autosave_timer.stop()
            self.state_store.clear_autosave()
        self.setWindowTitle(title)

    def _write_autosave(self):
        if not self._dirty or self._restoring_state:
            return
        payload = {
            "current_project_path": self._current_project_path,
            "project_state": self._snapshot_state(),
        }
        self.state_store.save_autosave(payload)

    def _maybe_restore_autosave(self):
        payload = self.state_store.load_autosave()
        if not payload:
            return
        if self._is_headless():
            return
        reply = QMessageBox.question(
            self,
            "Restore autosave",
            "An autosaved session was found. Do you want to restore it?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            self.state_store.clear_autosave()
            return
        missing = self._restore_state(payload.get("project_state", {}), mark_dirty=True)
        self._current_project_path = payload.get("current_project_path")
        self._set_dirty(True)
        if missing:
            msg = "Some autosaved data files were missing and related curves were skipped:\n\n" + "\n".join(
                f"- {k}: {p}" for k, p in missing
            )
            QMessageBox.warning(self, "Missing data files", msg)

    def _initialize_plot_mode(self, initial_plot_mode, prompt_for_mode):
        if self.controller.curves or self.controller.data_files:
            self._apply_plot_mode_ui()
            self._show_workspace()
            return

        if initial_plot_mode:
            self._activate_plot_mode(initial_plot_mode)
            return

        if self._is_headless() or not prompt_for_mode:
            self._activate_plot_mode(getattr(self.controller.config, "plot_mode", "line2d"))
            return

        default_mode = getattr(self.controller.config, "plot_mode", "line2d")
        self.landing_page.select_mode(default_mode)
        self._show_landing_page()

    def _activate_plot_mode(self, mode):
        self.controller.config.plot_mode = mode
        self._set_default_color_mode_for_context(mode)
        self._apply_plot_mode_ui()
        self.controller.update_plot()
        self._show_workspace()

    def _apply_plot_mode_ui(self):
        plot_mode = getattr(self.controller.config, "plot_mode", "line2d")
        needs_z = plot_mode_requires_z(plot_mode)
        supports_secondary_axis = plot_mode_supports_secondary_axis(plot_mode)
        current_3d_style = self._current_3d_style()
        supports_color_mode = plot_mode == "heatmap2d" or (plot_mode == "plot3d" and current_3d_style in {"surface", "volume"})
        uses_colormap = self._current_uses_colormap() if supports_color_mode else render_style_uses_colormap(plot_mode, current_3d_style)
        supports_direct_color = (plot_mode_supports_direct_color(plot_mode) or supports_color_mode) and not uses_colormap
        supports_render_style = plot_mode_supports_render_style(plot_mode)
        supports_z_ticks = plot_mode_supports_z_ticks(plot_mode)
        show_palette = plot_mode == "line2d" or uses_colormap

        self.plot_mode_value.setText(friendly_plot_mode(plot_mode))
        self.z_column_label.setText("Z column" if plot_mode == "plot3d" else "Z / value column")
        self.z_column_label.setVisible(needs_z)
        self.z_combo.setVisible(needs_z)
        self.z_ticks_label.setVisible(supports_z_ticks)
        self.z_ticks_edit.setVisible(supports_z_ticks)
        self.axis_label.setVisible(supports_secondary_axis)
        self.axis_combo.setVisible(supports_secondary_axis)
        self.render_style_label.setVisible(supports_render_style)
        self.render_style_combo.setVisible(supports_render_style)
        self.color_mode_label.setVisible(supports_color_mode)
        self.color_mode_combo.setVisible(supports_color_mode)
        self.palette_label.setText("Colormap" if uses_colormap else "Palette")
        self.palette_label.setVisible(show_palette)
        self.palette_combo.setVisible(show_palette)
        self.color_label.setText("Solid color" if supports_color_mode else "Curve color")
        self.color_label.setVisible(supports_direct_color)
        self.color_combo.setVisible(supports_direct_color)
        self.show_colorbar_checkbox.setVisible(uses_colormap and supports_color_mode)
        self.colorbar_label.setVisible(uses_colormap and supports_color_mode)
        self.colorbar_label_edit.setVisible(uses_colormap and supports_color_mode)
        self.add_curve_btn.setText(
            "Add heatmap" if plot_mode == "heatmap2d"
            else f"Add {friendly_3d_style(current_3d_style).lower()}" if plot_mode == "plot3d"
            else "Add curve"
        )

    def _current_3d_style(self):
        idx = self.curve_list.currentRow()
        if idx >= 0 and idx < len(self.controller.curves):
            return getattr(self.controller.curves[idx], "render_style", "line")
        return self.render_style_combo.currentData() or "line"

    def _current_uses_colormap(self):
        idx = self.curve_list.currentRow()
        if idx >= 0 and idx < len(self.controller.curves):
            return getattr(self.controller.curves[idx], "uses_colormap", True)
        return (self.color_mode_combo.currentData() or "colormap") == "colormap"

    def _has_selected_curve(self):
        idx = self.curve_list.currentRow()
        return 0 <= idx < len(self.controller.curves)

    def _curve_display_name(self, curve):
        return curve.display_name(getattr(self.controller.config, "plot_mode", "line2d"))

    def _restore_state(self, state_obj, *, mark_dirty=False):
        self._restoring_state = True
        try:
            missing = self.controller.load_state_obj(state_obj)
            self._refresh_all_ui()
            self._show_workspace()
        finally:
            self._restoring_state = False
        self._set_dirty(mark_dirty)
        return missing

    def _refresh_all_ui(self):
        self._apply_plot_mode_ui()
        self.refresh_files_list()
        self.populate_all_columns()
        self.refresh_curve_list()
        self.refresh_subplot_list()
        rows, cols = self.controller.config.subplot_layout
        self.populate_subplot_indices(rows * cols - 1)
        self.dimension_combo.blockSignals(True)
        self.dimension_combo.setCurrentText(str(tuple(self.controller.config.ratio)).replace(" ", ""))
        self.dimension_combo.blockSignals(False)
        if self.controller.curves:
            self.curve_list.setCurrentRow(0)
            self.on_curve_selected(0)
        else:
            self.curve_name_edit.clear()
        self.on_file_selected(self.files_list.currentRow())
        self.load_axes_widgets()

    def _refresh_recent_projects(self):
        current = self.recent_projects_combo.currentData()
        projects = self.state_store.load_recent_projects()
        self.recent_projects_combo.blockSignals(True)
        self.recent_projects_combo.clear()
        for path in projects:
            self.recent_projects_combo.addItem(Path(path).name, path)
        if current:
            idx = self.recent_projects_combo.findData(current)
            if idx >= 0:
                self.recent_projects_combo.setCurrentIndex(idx)
        self.recent_projects_combo.blockSignals(False)

    def _remember_project_path(self, path):
        self._current_project_path = os.path.abspath(path)
        self.state_store.remember_project(self._current_project_path)
        self._refresh_recent_projects()

    def _update_history_actions(self):
        self.undo_btn.setEnabled(bool(self._undo_stack))
        self.redo_btn.setEnabled(bool(self._redo_stack))

    def _confirm_discard_changes(self):
        if self._is_headless():
            return True
        if not self._dirty:
            return True
        reply = QMessageBox.question(
            self,
            "Unsaved changes",
            "Save changes before continuing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if reply == QMessageBox.Cancel:
            return False
        if reply == QMessageBox.Save:
            return self.save_project()
        return True

    def _is_headless(self):
        return os.getenv("QT_QPA_PLATFORM") == "offscreen"

    def undo(self):
        if not self._undo_stack:
            return
        current = self._snapshot_state()
        target = self._undo_stack.pop()
        self._redo_stack.append(current)
        self._restore_state(target, mark_dirty=True)
        self._update_history_actions()

    def redo(self):
        if not self._redo_stack:
            return
        current = self._snapshot_state()
        target = self._redo_stack.pop()
        self._undo_stack.append(current)
        self._restore_state(target, mark_dirty=True)
        self._update_history_actions()

    def on_file_selected(self, idx):
        if idx < 0:
            self.file_preview.clear()
            return
        item = self.files_list.item(idx)
        if item is None:
            self.file_preview.clear()
            return
        file_key = item.data(Qt.UserRole)
        self.file_preview.setPlainText(self._preview_file_text(file_key))

    def _preview_file_text(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.rstrip("\n") for _, line in zip(range(12), f)]
        except Exception as exc:
            return f"Unable to preview file:\n{exc}"
        return "\n".join(lines)

    def export_plot(self, fmt):
        filters = {
            "png": "PNG Image (*.png)",
            "svg": "SVG Image (*.svg)",
            "pdf": "PDF File (*.pdf)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export {fmt.upper()}",
            "",
            filters[fmt],
        )
        if not path:
            return
        if not path.lower().endswith(f".{fmt}"):
            path += f".{fmt}"
        self.canvas.fig.savefig(path, dpi=300 if fmt == "png" else None, bbox_inches="tight")

    def open_recent_project(self):
        path = self.recent_projects_combo.currentData()
        if path:
            self.open_project(path=path)

    # ------------------------------------------------------------------
    # Handlers: axis labels
    # ------------------------------------------------------------------
    def on_xlabel_changed(self):
        """Update config xlabel when user commits the edit."""
        self.apply_subplot_labels()
        self.controller.update_plot()

    def on_ylabel_changed(self):
        """Update config ylabel when user commits the edit."""
        self.apply_subplot_labels()
        self.controller.update_plot()

    # ------------------------------------------------------------------
    # Handlers: palette
    # ------------------------------------------------------------------
    def on_palette_changed(self, name: str):
        self.color_combo.blockSignals(True)
        populate_color_combo(self.color_combo, PLOTLY_PALETTES[name])
        self.color_combo.blockSignals(False)

        idx = self.curve_list.currentRow()
        if 0 <= idx < len(self.controller.curves):
            before_state = self._snapshot_state()
            c = self.controller.curves[idx]
            c.palette_name = name
            c.color = selected_color(self.color_combo)
            self.controller.update_plot()
            self._finalize_state_change(before_state)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------
    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open data file",
            "",
            "Data Files (*.csv *.txt *.dat);;CSV Files (*.csv);;Text Files (*.txt *.dat);;All Files (*)"
        )
        if not path:
            return

        try:
            before_state = self._snapshot_state()
            data_file = load_data_file(path)
            file_key = os.path.abspath(path)
            self.controller.data_files[file_key] = data_file
            self.refresh_files_list()
            self.populate_all_columns()
            self._select_default_columns_for_file(file_key)
            for i in range(self.files_list.count()):
                item = self.files_list.item(i)
                if item.data(Qt.UserRole) == file_key:
                    self.files_list.setCurrentRow(i)
                    break
            self._finalize_state_change(before_state)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def refresh_files_list(self):
        current_key = None
        if self.files_list.currentRow() >= 0 and self.files_list.item(self.files_list.currentRow()):
            current_key = self.files_list.item(self.files_list.currentRow()).data(Qt.UserRole)
        self.files_list.blockSignals(True)
        self.files_list.clear()
        for file_key in self.controller.data_files:
            item = QListWidgetItem(self._display_name_for_key(file_key))
            item.setData(Qt.UserRole, file_key)
            self.files_list.addItem(item)
        if self.files_list.count():
            selected = 0
            if current_key is not None:
                for i in range(self.files_list.count()):
                    if self.files_list.item(i).data(Qt.UserRole) == current_key:
                        selected = i
                        break
            self.files_list.setCurrentRow(selected)
        self.files_list.blockSignals(False)
        self.on_file_selected(self.files_list.currentRow())

    def remove_selected_file(self):
        idx = self.files_list.currentRow()
        if idx < 0:
            return

        before_state = self._snapshot_state()
        file_key = self.files_list.item(idx).data(Qt.UserRole)
        self.controller.remove_file(file_key)
        self.refresh_files_list()
        self.populate_all_columns()
        self.refresh_curve_list()
        self.controller.update_plot()
        self.on_file_selected(self.files_list.currentRow())
        self._finalize_state_change(before_state)

    # ------------------------------------------------------------------
    # Column population (all files)
    # ------------------------------------------------------------------
    def populate_all_columns(self):
        """
        Populate column combos with items formatted:
            "filename: column"
        This lets you use X/Y/Z from one or more files.
        """
        self.x_combo.blockSignals(True)
        self.y_combo.blockSignals(True)
        self.z_combo.blockSignals(True)

        self.x_combo.clear()
        self.y_combo.clear()
        self.z_combo.clear()

        for file_key in sorted(self.controller.data_files.keys()):
            data_file = self.controller.data_files[file_key]
            display_name = self._display_name_for_key(file_key)
            for col_name in data_file.headers:
                display_text = f"{display_name}: {col_name}"
                user_data = (file_key, col_name)
                self.x_combo.addItem(display_text, user_data)
                self.y_combo.addItem(display_text, user_data)
                self.z_combo.addItem(display_text, user_data)

        self.x_combo.blockSignals(False)
        self.y_combo.blockSignals(False)
        self.z_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Curve operations
    # ------------------------------------------------------------------
    def refresh_curve_list(self):
        """Rebuild curve list widget from controller state."""
        self.curve_list.blockSignals(True)
        self.curve_list.clear()
        for c in self.controller.curves:
            item = QListWidgetItem(self._curve_display_name(c))
            item.setData(Qt.UserRole, c)
            self.curve_list.addItem(item)
        self.curve_list.blockSignals(False)

    def on_curve_rows_reordered_from_list(self, *args):
        ordered_curves = []
        for row in range(self.curve_list.count()):
            item = self.curve_list.item(row)
            curve = item.data(Qt.UserRole) if item is not None else None
            if curve in self.controller.curves and curve not in ordered_curves:
                ordered_curves.append(curve)

        if len(ordered_curves) != len(self.controller.curves):
            self.refresh_curve_list()
            return

        before_state = self._snapshot_state()
        self.controller.curves = ordered_curves
        self.controller.update_plot()
        self._finalize_state_change(before_state)

    def add_curve(self):
        if not self.controller.data_files:
            return

        plot_mode = getattr(self.controller.config, "plot_mode", "line2d")
        x_data = self.x_combo.currentData(Qt.UserRole)
        y_data = self.y_combo.currentData(Qt.UserRole)
        z_data = self.z_combo.currentData(Qt.UserRole)

        if not x_data or not y_data or (plot_mode_requires_z(plot_mode) and not z_data):
            message = "Please select valid X, Y, and Z columns" if plot_mode_requires_z(plot_mode) else "Please select valid columns"
            QMessageBox.warning(self, "Error", message)
            return

        selected_columns = [x_data, y_data]
        if plot_mode_requires_z(plot_mode):
            selected_columns.append(z_data)
        if not self._selected_columns_have_matching_lengths(selected_columns):
            self._show_column_length_mismatch_warning()
            self._fallback_column_selection(selected_columns)
            return

        x_file_name, x_col = x_data
        y_file_name, y_col = y_data
        z_file_name = z_col = None
        if z_data:
            z_file_name, z_col = z_data

        x_data_file = self.controller.data_files[x_file_name]
        y_data_file = self.controller.data_files[y_file_name]
        z_data_file = self.controller.data_files[z_file_name] if z_file_name else None
        file_name = x_file_name
        data_file = x_data_file
        render_style = self.render_style_combo.currentData() or "line"
        uses_colormap = self._new_curve_uses_colormap(plot_mode, render_style)
        before_state = self._snapshot_state()
        self.controller.add_curve(
            file_name,
            data_file,
            x_col,
            y_col,
            self.axis_combo.currentText() if plot_mode_supports_secondary_axis(plot_mode) else "primary",
            selected_color(self.color_combo),
            self.palette_combo.currentText(),
            render_style=render_style if plot_mode == "plot3d" else "line",
            x_data_file=x_data_file,
            y_data_file=y_data_file,
            z_col=z_col if plot_mode_requires_z(plot_mode) else None,
            z_data_file=z_data_file if plot_mode_requires_z(plot_mode) else None,
            uses_colormap=uses_colormap,
            show_colorbar=self.show_colorbar_checkbox.isChecked() if uses_colormap else False,
            colorbar_label=self.colorbar_label_edit.text().strip() or None,
            opacity=self.opacity_slider.value() / 100.0,
        )
        self.refresh_curve_list()
        new_idx = len(self.controller.curves) - 1
        self.curve_list.setCurrentRow(new_idx)
        self.on_curve_selected(new_idx)
        self.controller.update_plot()
        self._finalize_state_change(before_state)

    def remove_selected_curve(self):
        idx = self.curve_list.currentRow()
        if idx < 0:
            return

        before_state = self._snapshot_state()
        self.controller.remove_curve(idx)
        self.refresh_curve_list()
        self.controller.update_plot()
        self._finalize_state_change(before_state)

    # ------------------------------------------------------------------
    # Curve selection -> UI synchronization
    # ------------------------------------------------------------------
    def on_curve_selected(self, idx: int):
        """
        When the user selects a curve in the list, update all widgets to match it.
        We block signals so setting widget values doesn't trigger change handlers.
        """
        if idx < 0 or idx >= len(self.controller.curves):
            return
        c = self.controller.curves[idx]
        plot_mode = getattr(self.controller.config, "plot_mode", "line2d")

        widgets_to_block = [
            self.x_combo, self.y_combo, self.z_combo, self.axis_combo, self.curve_name_edit,
            self.render_style_combo,
            self.palette_combo, self.color_combo, self.subplot_index_combo,
            self.color_mode_combo, self.show_colorbar_checkbox, self.colorbar_label_edit,
            self.opacity_slider,
        ]
        for w in widgets_to_block:
            w.blockSignals(True)

        self.curve_name_edit.setText(c.name)
        self.subplot_index_combo.setCurrentText(str(c.subplot_index))

        x_file_name = self._find_key_for_data_file(c.x_data_file)
        y_file_name = self._find_key_for_data_file(c.y_data_file)
        z_file_name = self._find_key_for_data_file(c.z_data_file) if c.z_data_file is not None else None

        if x_file_name:
            self._set_combo_to_column(self.x_combo, x_file_name, c.x_col)

        if y_file_name:
            self._set_combo_to_column(self.y_combo, y_file_name, c.y_col)

        if z_file_name and c.z_col:
            self._set_combo_to_column(self.z_combo, z_file_name, c.z_col)

        if plot_mode_supports_secondary_axis(plot_mode):
            self.axis_combo.setCurrentText(c.axis)
        if plot_mode_supports_render_style(plot_mode):
            render_idx = self.render_style_combo.findData(getattr(c, "render_style", "line"))
            if render_idx >= 0:
                self.render_style_combo.setCurrentIndex(render_idx)
        self.palette_combo.setCurrentText(c.palette_name)
        populate_color_combo(self.color_combo, PLOTLY_PALETTES[c.palette_name])
        ensure_color_in_combo(self.color_combo, c.color)
        mode = "colormap" if getattr(c, "uses_colormap", False) else "solid"
        mode_idx = self.color_mode_combo.findData(mode)
        if mode_idx >= 0:
            self.color_mode_combo.setCurrentIndex(mode_idx)
        self.show_colorbar_checkbox.setChecked(getattr(c, "show_colorbar", True))
        self.colorbar_label_edit.setText(getattr(c, "colorbar_label", "") or "")
        self.opacity_slider.setValue(int(round(getattr(c, "opacity", 1.0) * 100)))
        for w in widgets_to_block:
            w.blockSignals(False)
        self._apply_plot_mode_ui()

    # ------------------------------------------------------------------
    # Curve edits -> controller update
    # ------------------------------------------------------------------
    def on_curve_settings_changed(self, *args):

        idx = self.curve_list.currentRow()
        if idx < 0 or idx >= len(self.controller.curves):
            return

        before_state = self._snapshot_state()
        c = self.controller.curves[idx]
        plot_mode = getattr(self.controller.config, "plot_mode", "line2d")
        c.name = self.curve_name_edit.text().strip() or c.name

        x_data = self.x_combo.currentData(Qt.UserRole)
        y_data = self.y_combo.currentData(Qt.UserRole)
        z_data = self.z_combo.currentData(Qt.UserRole)

        selected_columns = []
        if x_data:
            selected_columns.append(x_data)
        elif self._find_key_for_data_file(c.x_data_file):
            selected_columns.append((self._find_key_for_data_file(c.x_data_file), c.x_col))

        if y_data:
            selected_columns.append(y_data)
        elif self._find_key_for_data_file(c.y_data_file):
            selected_columns.append((self._find_key_for_data_file(c.y_data_file), c.y_col))

        if plot_mode_requires_z(plot_mode):
            if z_data:
                selected_columns.append(z_data)
            elif c.z_data_file is not None and self._find_key_for_data_file(c.z_data_file):
                selected_columns.append((self._find_key_for_data_file(c.z_data_file), c.z_col))

        if not self._selected_columns_have_matching_lengths(selected_columns):
            self._show_column_length_mismatch_warning()
            self._fallback_column_selection(selected_columns, curve_index=idx)
            return

        if x_data:
            x_file_name, x_col = x_data
            c.x_data_file = self.controller.data_files[x_file_name]
            c.file_name = x_file_name
        else:
            x_col = c.x_col

        if y_data:
            y_file_name, y_col = y_data
            c.y_data_file = self.controller.data_files[y_file_name]
        else:
            y_col = c.y_col

        if plot_mode_requires_z(plot_mode) and z_data:
            z_file_name, z_col = z_data
            c.z_data_file = self.controller.data_files[z_file_name]
        else:
            z_col = c.z_col

        render_style = self.render_style_combo.currentData() or getattr(c, "render_style", "line")
        uses_colormap = self._new_curve_uses_colormap(plot_mode, render_style)
        self.controller.update_curve(
            idx,
            x_col,
            y_col,
            self.axis_combo.currentText() if plot_mode_supports_secondary_axis(plot_mode) else "primary",
            selected_color(self.color_combo),
            c.palette_name,
            subplot_index=int(self.subplot_index_combo.currentText() or "0"),
            z_col=z_col if plot_mode_requires_z(plot_mode) else c.z_col,
            render_style=render_style if plot_mode == "plot3d" else "line",
            uses_colormap=uses_colormap,
            show_colorbar=self.show_colorbar_checkbox.isChecked() if uses_colormap else False,
            colorbar_label=self.colorbar_label_edit.text().strip() or None,
            opacity=self.opacity_slider.value() / 100.0,
        )

        item = self.curve_list.item(idx)

        if item is not None:
            item.setText(self._curve_display_name(self.controller.curves[idx]))
        else:
            self.refresh_curve_list()
            self.curve_list.setCurrentRow(idx)

        self.curve_list.setCurrentRow(idx)
        self._apply_plot_mode_ui()

        self.controller.update_plot()
        self._finalize_state_change(before_state)

    def _new_curve_uses_colormap(self, plot_mode, render_style):
        if plot_mode == "heatmap2d":
            return (self.color_mode_combo.currentData() or "colormap") == "colormap"
        if plot_mode == "plot3d" and render_style in {"surface", "volume"}:
            return (self.color_mode_combo.currentData() or "colormap") == "colormap"
        return False

    def _set_default_color_mode_for_context(self, plot_mode):
        default_mode = "colormap" if plot_mode == "heatmap2d" else "solid"
        index = self.color_mode_combo.findData(default_mode)
        if index >= 0:
            self.color_mode_combo.blockSignals(True)
            self.color_mode_combo.setCurrentIndex(index)
            self.color_mode_combo.blockSignals(False)
        self.show_colorbar_checkbox.blockSignals(True)
        self.show_colorbar_checkbox.setChecked(default_mode == "colormap")
        self.show_colorbar_checkbox.blockSignals(False)

    # ------------------------------------------------------------------
    # Canvas settings -> config update
    # ------------------------------------------------------------------
    def on_canvas_settings_changed(self, *args):

        dim_text = self.dimension_combo.currentText()
        try:
            before_state = self._snapshot_state()
            self.apply_subplot_ticks()
            self.controller.config.ratio = literal_eval(dim_text)
            self.controller.update_plot()
            self._finalize_state_change(before_state)
        except Exception:
            pass

    def open_advanced_dialog(self):
        dlg = AdvancedDialog(self.controller.config, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            before_state = self._snapshot_state()
            dlg.apply_to_config()
            self.controller.normalize_curve_subplots()
            self.controller.update_plot()
            max_index = dlg.get_max_subplot_index()
            self.populate_subplot_indices(max_index)
            self.refresh_subplot_list()
            self._finalize_state_change(before_state)

    def populate_subplot_indices(self, max_index):
        self.subplot_index_combo.blockSignals(True)
        try:
            current = self.subplot_index_combo.currentText()
            self.subplot_index_combo.clear()
            self.subplot_index_combo.addItems([str(i) for i in range(max_index + 1)])
            if current:
                self.subplot_index_combo.setCurrentText(current)
        finally:
            self.subplot_index_combo.blockSignals(False)

    def refresh_subplot_list(self):
        rows, cols = self.controller.config.subplot_layout
        n = rows * cols

        is_subplots = (n > 1)
        self.subplot_label.setVisible(is_subplots)
        self.subplot_list.setVisible(is_subplots)


        if not is_subplots:
            self._active_subplot = None
            self.subplot_list.blockSignals(True)
            self.subplot_list.clear()
            self.subplot_list.blockSignals(False)
            self.subplot_label.setVisible(False)
            self.subplot_list.setVisible(False)
            return

        self.subplot_list.blockSignals(True)
        self.subplot_list.clear()
        for i in range(n):
            r, c = divmod(i, cols)
            self.subplot_list.addItem(f"Subplot {i}  (r{r}, c{c})")
        self.subplot_list.blockSignals(False)

        # Auto-select 0 if nothing selected
        if self.subplot_list.currentRow() < 0:
            self.subplot_list.setCurrentRow(0)

    def on_subplot_selected(self, idx):
        if idx < 0:
            self._active_subplot = None
        else:
            self._active_subplot = idx
        subplot_index = self._active_subplot
        # subplot_config = self.controller.config.subplots_config[subplot_index]

        self.load_axes_widgets()

    def load_axes_widgets(self):
        cfg = self.controller.config

        if self._active_subplot is None:
            ov = {}
        else:
            ov = cfg.subplots_config.get(self._active_subplot, {})
        # Block signals to avoid triggering handlers while setting values
        # self.xlabel_edit.blockSignals(True)
        # self.ylabel_edit.blockSignals(True)
        # self.x_min_edit.blockSignals(True)
        # self.x_max_edit.blockSignals(True)
        # self.y_min_edit.blockSignals(True)
        # self.y_max_edit.blockSignals(True)
        self.x_ticks_edit.blockSignals(True)
        self.y_ticks_edit.blockSignals(True)
        self.z_ticks_edit.blockSignals(True)



        # xlabel = ov.get("xlabel", cfg.xlabel)
        # ylabel = ov.get("ylabel", cfg.ylabel)
        # xlim   = ov.get("xlim", cfg.xlimits)
        # ylim   = ov.get("ylim", cfg.ylimits)
        xtN    = ov.get("xticksN", cfg.xticksN)
        ytN    = ov.get("yticksN", cfg.yticksN)
        ztN    = ov.get("zticksN", cfg.zticksN)

        # --- fill widgets ---
        # self.xlabel_edit.setText(xlabel or "")
        # self.ylabel_edit.setText(ylabel or "")

        # self.x_min_edit.setText("" if not xlim or xlim[0] is None else str(xlim[0]))
        # self.x_max_edit.setText("" if not xlim or xlim[1] is None else str(xlim[1]))
        # self.y_min_edit.setText("" if not ylim or ylim[0] is None else str(ylim[0]))
        # self.y_max_edit.setText("" if not ylim or ylim[1] is None else str(ylim[1]))

        if xtN is not None:
            self.x_ticks_edit.setValue(int(xtN))
        if ytN is not None:
            self.y_ticks_edit.setValue(int(ytN))
        if ztN is not None:
            self.z_ticks_edit.setValue(int(ztN))

        # Unblock signals
        # self.xlabel_edit.blockSignals(False)
        # self.ylabel_edit.blockSignals(False)
        # self.x_min_edit.blockSignals(False)
        # self.x_max_edit.blockSignals(False)
        # self.y_min_edit.blockSignals(False)
        # self.y_max_edit.blockSignals(False)
        self.x_ticks_edit.blockSignals(False)
        self.y_ticks_edit.blockSignals(False)
        self.z_ticks_edit.blockSignals(False)

    def apply_subplot_labels(self):
        cfg = self.controller.config

        # xtext = self.xlabel_edit.text().strip()
        # ytext = self.ylabel_edit.text().strip()

        # No subplot selected -> write global
        if self._active_subplot is None:
            # cfg.xlabel = xtext
            # cfg.ylabel = ytext
            return

        rows, cols = cfg.subplot_layout
        i0 = int(self._active_subplot)
        r0, c0 = divmod(i0, cols)

        # ---- X label handling ----
        # if cfg.shared_x:
        #     # shared_x => xlabel is per COLUMN
        #     for r in range(rows):
        #         i = r * cols + c0
        #         ov = cfg.subplots_config.setdefault(i, {})
        #         # ov["xlabel"] = xtext
        # else:
        #     ov = cfg.subplots_config.setdefault(i0, {})
        #     ov["xlabel"] = xtext

        # ---- Y label handling ----
        # if cfg.shared_y:
        #     # shared_y => ylabel is per ROW (symmetry; change if you prefer per column)
        #     for c in range(cols):
        #         i = r0 * cols + c
        #         ov = cfg.subplots_config.setdefault(i, {})
        #         ov["ylabel"] = ytext
        # else:
            # ov = cfg.subplots_config.setdefault(i0, {})
            # ov["ylabel"] = ytext

    def apply_subplot_limits(self):
        cfg = self.controller.config

        # xmin_text = self.x_min_edit.text().strip()
        # xmax_text = self.x_max_edit.text().strip()
        # ymin_text = self.y_min_edit.text().strip()
        # ymax_text = self.y_max_edit.text().strip()

        # No subplot selected -> write global
        if self._active_subplot is None:
            cfg.xlimits = (
                float(xmin_text) if xmin_text else None,
                float(xmax_text) if xmax_text else None,
            )
            cfg.ylimits = (
                float(ymin_text) if ymin_text else None,
                float(ymax_text) if ymax_text else None,
            )
            return

        rows, cols = cfg.subplot_layout
        i0 = int(self._active_subplot)
        r0, c0 = divmod(i0, cols)

        # ---- X limits handling ----
        if cfg.shared_x:
            # shared_x => xlimits is per COLUMN
            for r in range(rows):
                i = r * cols + c0
                ov = cfg.subplots_config.setdefault(i, {})
                ov["xlim"] = (
                    float(xmin_text) if xmin_text else None,
                    float(xmax_text) if xmax_text else None,
                )
        else:
            ov = cfg.subplots_config.setdefault(i0, {})
            ov["xlim"] = (
                float(xmin_text) if xmin_text else None,
                float(xmax_text) if xmax_text else None,
            )

        # ---- Y limits handling ----
        if cfg.shared_y:
            # shared_y => ylimits is per ROW
            for c in range(cols):
                i = r0 * cols + c
                ov = cfg.subplots_config.setdefault(i, {})
                ov["ylim"] = (
                    float(ymin_text) if ymin_text else None,
                    float(ymax_text) if ymax_text else None,
                )
        else:
            ov = cfg.subplots_config.setdefault(i0, {})
            ov["ylim"] = (
                float(ymin_text) if ymin_text else None,
                float(ymax_text) if ymax_text else None,
            )

    def apply_subplot_ticks(self):
        cfg = self.controller.config
        xtN = self.x_ticks_edit.value()
        ytN = self.y_ticks_edit.value()
        ztN = self.z_ticks_edit.value()
        # No subplot selected -> write global
        if self._active_subplot is None:
            cfg.xticksN = xtN
            cfg.yticksN = ytN
            cfg.zticksN = ztN
            return
        rows, cols = cfg.subplot_layout
        i0 = int(self._active_subplot)
        r0, c0 = divmod(i0, cols)

        # ---- X ticks handling ----
        if cfg.shared_x:
            # shared_x => xticksN is per COLUMN
            for r in range(rows):
                i = r * cols + c0
                ov = cfg.subplots_config.setdefault(i, {})
                ov["xticksN"] = xtN
        else:
            ov = cfg.subplots_config.setdefault(i0, {})
            ov["xticksN"] = xtN

        # ---- Y ticks handling ----
        if cfg.shared_y:
            # shared_y => yticksN is per ROW
            for c in range(cols):
                i = r0 * cols + c
                ov = cfg.subplots_config.setdefault(i, {})
                ov["yticksN"] = ytN
        else:
            ov = cfg.subplots_config.setdefault(i0, {})
            ov["yticksN"] = ytN

        ov = cfg.subplots_config.setdefault(i0, {})
        ov["zticksN"] = ztN

    def _sync_labels_from_mpl(self, event=None):
        if self._skip_next_draw_event:
            self._skip_next_draw_event = False
            return
        if self._mpl_label_sync_guard:
            return
        self._mpl_label_sync_guard = True
        
        try:
            cfg = self.controller.config
            axes = getattr(self.canvas, "axes", [])
            if not axes:
                return

            rows, cols = cfg.subplot_layout

            # -------------------------
            # X LABELS
            # -------------------------
            if cfg.shared_x:
                # In your plotting code, only bottom row shows xlabel.
                bottom_r = rows - 1
                for c in range(cols):
                    i_bottom = bottom_r * cols + c
                    if i_bottom >= len(axes):
                        continue
                    xlab = axes[i_bottom].get_xlabel()

                    # store per column in subplots_config (your apply_subplot_labels logic style)
                    for r in range(rows):
                        i = r * cols + c
                        cfg.subplots_config.setdefault(i, {})["xlabel"] = xlab

                # keep a global fallback
                cfg.xlabel = axes[(rows - 1) * cols].get_xlabel() or cfg.xlabel

            else:
                # per subplot
                for i, ax in enumerate(axes):
                    cfg.subplots_config.setdefault(i, {})["xlabel"] = ax.get_xlabel()


                cfg.xlabel = axes[0].get_xlabel() or cfg.xlabel


            # -------------------------
            # Y LABELS
            # -------------------------
            if cfg.shared_y:
                # You treat shared_y as "per row" (see your apply_subplot_labels)
                for r in range(rows):
                    i_left = r * cols
                    if i_left >= len(axes):
                        continue
                    ylab = axes[i_left].get_ylabel()

                    for c in range(cols):
                        i = r * cols + c
                        cfg.subplots_config.setdefault(i, {})["ylabel"] = ylab

                cfg.ylabel = axes[0].get_ylabel() or cfg.ylabel

            else:
                # per subplot
                for i, ax in enumerate(axes):
                    cfg.subplots_config.setdefault(i, {})["ylabel"] = ax.get_ylabel()

                cfg.ylabel = axes[0].get_ylabel() or cfg.ylabel

            # -------------------------
            # Markers
            # ------------------------
            # -------------------------
        # Sync markers from MPL artists (toolbar Customize)
        # -------------------------
        
            self.color_combo.blockSignals(True)
            self.palette_combo.blockSignals(True)
            for j, c in enumerate(self.controller.curves):
                line = getattr(c, "_mpl_line", None)
                if line is None:
                    continue

                selected_idx = self.curve_list.currentRow()
                m = line.get_marker()
                m_face_color = line.get_markerfacecolor()
                m_edge_color = line.get_markeredgecolor()
                ms = line.get_markersize()
                linestyle = line.get_linestyle()
                linewidth = line.get_linewidth()
                color= line.get_color()
                name = line.get_label()
                # if color is rba, convert to hex
                if isinstance(color, tuple) and len(color) == 4:
                    r, g, b, a = color
                    r = int(round(r * 255))
                    g = int(round(g * 255))
                    b = int(round(b * 255))
                    color = f"#{r:02x}{g:02x}{b:02x}"


                # Normalize Matplotlib conventions to your model
                if m in (None, "", " ", "None"):
                    m = "None"

                c.marker = m
                if ms is not None:
                    c.marker_size = int(round(ms))
                c.linestyle = linestyle
                c.linewidth = float(linewidth)
                c.color = color
                c.marker_face_color = m_face_color
                c.marker_edge_color = m_edge_color
                c.name = name
                if j == selected_idx:
                    ensure_color_in_combo(self.color_combo, c.color)
            
            self.refresh_curve_list()
            self.canvas.refresh_legends(cfg)

            # Legend was rebuilt AFTER the draw_event → force one redraw so it becomes visible.
            self._skip_next_draw_event = True
            self.canvas.draw_idle()


        
        finally:
            
            self._mpl_label_sync_guard = False

            self.color_combo.blockSignals(False)
            self.palette_combo.blockSignals(False)
            
        # XY limits
        for i, ax in enumerate(getattr(self.canvas, "axes", [])):
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            subplot_cfg = cfg.subplots_config.setdefault(i, {})
            subplot_cfg["xlim"] = (xlim[0], xlim[1])
            subplot_cfg["ylim"] = (ylim[0], ylim[1])
            subplot_cfg["xticksN"] = max(1, len(ax.get_xticks()))
            subplot_cfg["yticksN"] = max(1, len(ax.get_yticks()))
            if hasattr(ax, "get_zticks"):
                subplot_cfg["zticksN"] = max(1, len(ax.get_zticks()))

        if getattr(self.controller.config, "plot_mode", "line2d") == "plot3d" and getattr(self.canvas, "axes", []):
            first_ax = self.canvas.axes[0]
            if hasattr(first_ax, "get_zticks"):
                cfg.zticksN = max(1, len(first_ax.get_zticks()))
                self.load_axes_widgets()


    def save_project(self, checked=False, path=None):
        if path is None and self._current_project_path:
            path = self._current_project_path
        path, _ = QFileDialog.getSaveFileName(
            self, "Save plot project", path or "", "Plot Project (*.pproj *.json)"
        ) if path is None else (path, "")
        if not path:
            return False
        if not (path.endswith(".pproj") or path.endswith(".json")):
            path += ".pproj"
        self.controller.save_project(path)
        self._remember_project_path(path)
        self._set_dirty(False)
        return True

    def open_project(self, checked=False, path=None):
        if not self._confirm_discard_changes():
            return False
        if path is None:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open plot project", "", "Plot Project (*.pproj *.json)"
            )
        if not path:
            return False

        missing = self.controller.load_project(path)
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._update_history_actions()
        self._remember_project_path(path)
        self._refresh_all_ui()
        self._show_workspace()
        self._set_dirty(False)

        if missing:
            msg = "Some files were missing and related curves were skipped:\n\n" + "\n".join(
                f"- {k}: {p}" for k, p in missing
            )
            QMessageBox.warning(self, "Missing data files", msg)
        return True

    def _display_name_for_key(self, file_key: str) -> str:
        base = os.path.basename(file_key)
        siblings = [k for k in self.controller.data_files if os.path.basename(k) == base]
        if len(siblings) <= 1:
            return base

        parent = os.path.basename(os.path.dirname(file_key))
        parent_matches = [
            k for k in siblings
            if os.path.basename(os.path.dirname(k)) == parent
        ]
        if len(parent_matches) == 1:
            return f"{base} ({parent})"
        return file_key

    def _find_key_for_data_file(self, target):
        for file_key, data_file in self.controller.data_files.items():
            if data_file is target:
                return file_key
        return None

    def _set_combo_to_column(self, combo, file_key, column_name):
        wanted = (file_key, column_name)
        for i in range(combo.count()):
            if combo.itemData(i, Qt.UserRole) == wanted:
                combo.setCurrentIndex(i)
                return

    def _selected_columns_have_matching_lengths(self, selected_columns):
        lengths = []
        for selection in selected_columns:
            if not selection:
                continue
            file_key, column_name = selection
            data_file = self.controller.data_files.get(file_key)
            if data_file is None:
                return False
            lengths.append(len(data_file.get_column(column_name)))
        return len(set(lengths)) <= 1

    def _show_column_length_mismatch_warning(self):
        QMessageBox.warning(
            self,
            "Column length mismatch",
            "Selected X, Y, and Z columns must have the same number of rows.",
        )

    def _fallback_column_selection(self, selected_columns, curve_index=None):
        if curve_index is not None and 0 <= curve_index < len(self.controller.curves):
            self.on_curve_selected(curve_index)
            return

        for selection in selected_columns:
            if not selection:
                continue
            file_key, _ = selection
            if file_key in self.controller.data_files:
                self._select_default_columns_for_file(file_key)
                return

    def _select_default_columns_for_file(self, file_key):
        data_file = self.controller.data_files.get(file_key)
        if data_file is None or not data_file.headers:
            return

        defaults = [
            (self.x_combo, data_file.headers[0]),
            (self.y_combo, data_file.headers[1] if len(data_file.headers) > 1 else data_file.headers[0]),
            (self.z_combo, data_file.headers[2] if len(data_file.headers) > 2 else data_file.headers[-1]),
        ]

        for combo, column_name in defaults:
            combo.blockSignals(True)
            self._set_combo_to_column(combo, file_key, column_name)
            combo.blockSignals(False)
