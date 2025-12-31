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

import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QLabel, QListWidget, QLineEdit, QComboBox,
    QFileDialog, QMessageBox, QHBoxLayout, QVBoxLayout, QGridLayout, QSlider, QCheckBox, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer

from PlotCanvas import PlotCanvas
from AppController import AppController
from Color_modules import (
    PLOTLY_PALETTES,
    populate_color_combo,
    selected_color,
    ensure_color_in_combo,
)
from DataFile import load_data_file
from AdvancedDialog import *

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # -------------------------
        # Window + core objects
        # -------------------------
        self.setWindowTitle("Clean PyQt Plotter")
        self.resize(1000, 600)

        self.canvas = PlotCanvas()
        self.controller = AppController(self.canvas)

        # -------------------------
        # Debounced redraw on resize
        # -------------------------
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.controller.update_plot)

        # Build UI + connect signals
        self._build_ui()
        self._connect_signals()

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

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        """Top-level layout: left control panel + right plot canvas."""
        central = QWidget()
        self.setCentralWidget(central)

        self.main_layout = QHBoxLayout(central)

        # ---------------------------
# Scrollable control panel
# ---------------------------
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Container widget inside scroll area
        control_container = QWidget()
        self.control_layout = QVBoxLayout(control_container)

        scroll_area.setWidget(control_container)

        # Add to main layout
        self.main_layout.addWidget(scroll_area, 1)
        self.main_layout.addWidget(self.canvas, 3)


        # Build control sections (top → bottom)
        self._build_files_section()
        self._build_axis_labels_section()
        self._build_dimension_section()
        self._build_curves_section()
        self._build_color_section()
        self._build_marker_section()
        self._build_line_section()
        self._build_axis_limits_section()
        self._build_ticks_section()
        # self._build_grid_section()
        self._build_actions_section()

        self.control_layout.addStretch()

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

        self.control_layout.addWidget(QLabel("X column"))
        self.x_combo = QComboBox()
        self.control_layout.addWidget(self.x_combo)

        self.control_layout.addWidget(QLabel("Y column"))
        self.y_combo = QComboBox()
        self.control_layout.addWidget(self.y_combo)

        self.control_layout.addWidget(QLabel("Axis"))
        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["primary", "secondary"])
        self.control_layout.addWidget(self.axis_combo)

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
        # --- File actions ---
        self.add_file_btn.clicked.connect(self.load_file)
        self.remove_file_btn.clicked.connect(self.remove_selected_file)

        # --- Curve actions ---
        self.add_curve_btn.clicked.connect(self.add_curve)
        self.remove_curve_btn.clicked.connect(self.remove_selected_curve)
        self.curve_list.currentRowChanged.connect(self.on_curve_selected)

        # --- Axis label edits ---
        # editingFinished emits no args; we read the QLineEdit text in handler
        self.xlabel_edit.editingFinished.connect(self.on_xlabel_changed)
        self.ylabel_edit.editingFinished.connect(self.on_ylabel_changed)

        # --- Palette ---
        self.palette_combo.currentTextChanged.connect(self.on_palette_changed)

        # --- Curve live settings ---
        self.x_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.y_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.axis_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.curve_name_edit.editingFinished.connect(self.on_curve_settings_changed)

        self.color_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.marker_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.marker_size_combo.valueChanged.connect(self.on_curve_settings_changed)
        self.linestyle_combo.currentTextChanged.connect(self.on_curve_settings_changed)
        self.linewidth_combo.currentTextChanged.connect(self.on_curve_settings_changed)

        # --- Canvas settings ---
        self.dimension_combo.currentTextChanged.connect(self.on_canvas_settings_changed)
        self.x_min_edit.editingFinished.connect(self.on_canvas_settings_changed)
        self.x_max_edit.editingFinished.connect(self.on_canvas_settings_changed)
        self.y_min_edit.editingFinished.connect(self.on_canvas_settings_changed)
        self.y_max_edit.editingFinished.connect(self.on_canvas_settings_changed)
        self.x_ticks_edit.valueChanged.connect(self.on_canvas_settings_changed)
        self.y_ticks_edit.valueChanged.connect(self.on_canvas_settings_changed)
        # self.minor_ticks_checkbox.stateChanged.connect(self.on_canvas_settings_changed)
        # self.major_grid_checkbox.stateChanged.connect(self.on_canvas_settings_changed)
        # self.minor_grid_checkbox.stateChanged.connect(self.on_canvas_settings_changed)

        # --- Advanced dialog ---
        self.advanced_btn.clicked.connect(self.open_advanced_dialog)

        # --- Manual plot update ---
        self.plot_btn.clicked.connect(self.controller.update_plot)

    # ------------------------------------------------------------------
    # Handlers: axis labels
    # ------------------------------------------------------------------
    def on_xlabel_changed(self):
        """Update config xlabel when user commits the edit."""
        self.controller.config.xlabel = self.xlabel_edit.text().strip()
        self.controller.update_plot()

    def on_ylabel_changed(self):
        """Update config ylabel when user commits the edit."""
        self.controller.config.ylabel = self.ylabel_edit.text().strip()
        self.controller.update_plot()

    # ------------------------------------------------------------------
    # Handlers: palette
    # ------------------------------------------------------------------
    def on_palette_changed(self, name: str):
        """
        When palette changes:
        - rebuild the swatch combo
        - if a curve is selected, apply new palette + current swatch color
        """
        # Refresh swatch list without triggering curve updates mid-populate
        self.color_combo.blockSignals(True)
        populate_color_combo(self.color_combo, PLOTLY_PALETTES[name])
        self.color_combo.blockSignals(False)

        # Apply to selected curve (if any)
        idx = self.curve_list.currentRow()
        if 0 <= idx < len(self.controller.curves):
            c = self.controller.curves[idx]
            c.palette_name = name
            c.color = selected_color(self.color_combo)
            self.controller.update_plot()

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------
    def load_file(self):
        """Open a file picker, load data file, add it to controller.data_files."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open data file",
            "",
            "Data Files (*.csv *.txt *.dat);;CSV Files (*.csv);;Text Files (*.txt *.dat);;All Files (*)"
        )
        if not path:
            return

        try:
            file_name = os.path.basename(path)
            data_file = load_data_file(path)

            # Store by displayed filename (your UI expects this convention)
            self.controller.data_files[file_name] = data_file

            self.refresh_files_list()
            self.populate_all_columns()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def refresh_files_list(self):
        """Rebuild the file list widget from controller state."""
        self.files_list.blockSignals(True)
        self.files_list.clear()
        for file_name in self.controller.data_files:
            self.files_list.addItem(file_name)
        self.files_list.blockSignals(False)

    def remove_selected_file(self):
        """Remove the currently selected file from controller and refresh UI."""
        idx = self.files_list.currentRow()
        if idx < 0:
            return

        file_name = self.files_list.item(idx).text()
        self.controller.remove_file(file_name)

        self.refresh_files_list()
        self.populate_all_columns()
        self.controller.update_plot()

    # ------------------------------------------------------------------
    # Column population (all files)
    # ------------------------------------------------------------------
    def populate_all_columns(self):
        """
        Populate X/Y combos with items formatted:
            "filename: column"
        This lets you use X from one file and Y from another.
        """
        self.x_combo.blockSignals(True)
        self.y_combo.blockSignals(True)

        self.x_combo.clear()
        self.y_combo.clear()

        for file_name in sorted(self.controller.data_files.keys()):
            data_file = self.controller.data_files[file_name]
            for col_name in data_file.headers:
                display_text = f"{file_name}: {col_name}"
                self.x_combo.addItem(display_text)
                self.y_combo.addItem(display_text)

        self.x_combo.blockSignals(False)
        self.y_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Curve operations
    # ------------------------------------------------------------------
    def refresh_curve_list(self):
        """Rebuild curve list widget from controller state."""
        self.curve_list.blockSignals(True)
        self.curve_list.clear()
        for c in self.controller.curves:
            self.curve_list.addItem(c.display_name())
        self.curve_list.blockSignals(False)

    def add_curve(self):
        """Create a new curve using current UI settings."""
        if not self.controller.data_files:
            return

        x_text = self.x_combo.currentText()
        y_text = self.y_combo.currentText()

        if ": " not in x_text or ": " not in y_text:
            QMessageBox.warning(self, "Error", "Please select valid columns")
            return

        x_file_name, x_col = x_text.split(": ", 1)
        y_file_name, y_col = y_text.split(": ", 1)

        x_data_file = self.controller.data_files[x_file_name]
        y_data_file = self.controller.data_files[y_file_name]

        # Use x file as the "main" file for curve bookkeeping
        file_name = x_file_name
        data_file = x_data_file

        self.controller.add_curve(
            file_name,
            data_file,
            x_col,
            y_col,
            self.axis_combo.currentText(),
            selected_color(self.color_combo),
            self.palette_combo.currentText(),
            self.marker_combo.currentText(),
            self.marker_size_combo.value(),
            self.linestyle_combo.currentText(),
            float(self.linewidth_combo.currentText()),
            x_data_file=x_data_file,
            y_data_file=y_data_file,
        )

        self.refresh_curve_list()

        # Select the newly added curve and sync UI
        new_idx = len(self.controller.curves) - 1
        self.curve_list.setCurrentRow(new_idx)
        self.on_curve_selected(new_idx)

        self.controller.update_plot()

    def remove_selected_curve(self):
        """Remove selected curve from controller and redraw."""
        idx = self.curve_list.currentRow()
        if idx < 0:
            return

        self.controller.remove_curve(idx)
        self.refresh_curve_list()
        self.controller.update_plot()

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

        # Block signals for all widgets we will set
        widgets_to_block = [
            self.x_combo, self.y_combo, self.axis_combo, self.curve_name_edit,
            self.palette_combo, self.color_combo, self.marker_combo,
            self.marker_size_combo, self.linestyle_combo, self.linewidth_combo
        ]
        for w in widgets_to_block:
            w.blockSignals(True)

        # Basic properties
        self.curve_name_edit.setText(c.name)

        # Find file names matching x/y data files
        x_file_name = None
        y_file_name = None
        for fname, dfile in self.controller.data_files.items():
            if dfile is c.x_data_file:
                x_file_name = fname
            if dfile is c.y_data_file:
                y_file_name = fname

        # Select correct x/y entries in combos
        if x_file_name:
            wanted = f"{x_file_name}: {c.x_col}"
            for i in range(self.x_combo.count()):
                if self.x_combo.itemText(i) == wanted:
                    self.x_combo.setCurrentIndex(i)
                    break

        if y_file_name:
            wanted = f"{y_file_name}: {c.y_col}"
            for i in range(self.y_combo.count()):
                if self.y_combo.itemText(i) == wanted:
                    self.y_combo.setCurrentIndex(i)
                    break

        # Axis + style
        self.axis_combo.setCurrentText(c.axis)
        self.marker_combo.setCurrentText(c.marker)
        self.marker_size_combo.setValue(c.marker_size)
        self.linestyle_combo.setCurrentText(c.linestyle)
        self.linewidth_combo.setCurrentText(str(c.linewidth))
        self.palette_combo.setCurrentText(c.palette_name)

        # Rebuild swatches for this palette and ensure curve color exists/select it
        populate_color_combo(self.color_combo, PLOTLY_PALETTES[c.palette_name])
        ensure_color_in_combo(self.color_combo, c.color)

        # Unblock signals
        for w in widgets_to_block:
            w.blockSignals(False)

    # ------------------------------------------------------------------
    # Curve edits -> controller update
    # ------------------------------------------------------------------
    def on_curve_settings_changed(self, *args):
        """
        Called when any curve setting widget changes.
        Updates the currently selected curve in the controller.
        """
        idx = self.curve_list.currentRow()
        if idx < 0 or idx >= len(self.controller.curves):
            return

        c = self.controller.curves[idx]
        c.name = self.curve_name_edit.text().strip() or c.name

        # Parse "filename: column" from X/Y combos
        x_text = self.x_combo.currentText()
        y_text = self.y_combo.currentText()

        if ": " in x_text:
            x_file_name, x_col = x_text.split(": ", 1)
            c.x_data_file = self.controller.data_files[x_file_name]
        else:
            x_col = x_text

        if ": " in y_text:
            y_file_name, y_col = y_text.split(": ", 1)
            c.y_data_file = self.controller.data_files[y_file_name]
        else:
            y_col = y_text

        # Update curve in controller/model
        self.controller.update_curve(
            idx,
            x_col,
            y_col,
            self.axis_combo.currentText(),
            selected_color(self.color_combo),
            c.palette_name,
            self.marker_combo.currentText(),
            self.marker_size_combo.value(),
            self.linestyle_combo.currentText(),
            float(self.linewidth_combo.currentText()),
        )

        # Keep curve list in sync and keep selection
        self.refresh_curve_list()
        self.curve_list.setCurrentRow(idx)

        self.controller.update_plot()

    # ------------------------------------------------------------------
    # Canvas settings -> config update
    # ------------------------------------------------------------------
    def on_canvas_settings_changed(self, *args):

        """
        Update global canvas settings (ratio + axis limits).
        Limits accept empty entries meaning "auto".
        """
        dim_text = self.dimension_combo.currentText()

        xmin_text = self.x_min_edit.text().strip()
        xmax_text = self.x_max_edit.text().strip()
        ymin_text = self.y_min_edit.text().strip()
        ymax_text = self.y_max_edit.text().strip()

        self.controller.config.xticksN = self.x_ticks_edit.value()
        self.controller.config.yticksN = self.y_ticks_edit.value()
        # self.controller.config.minor_ticks = self.minor_ticks_checkbox.isChecked()
        # self.controller.config.minor_grid = self.minor_ticks_checkbox.isChecked()
        # self.controller.config.grid = self.major_grid_checkbox.isChecked()
        # self.controller.config.minor_grid = self.minor_grid_checkbox.isChecked()

        try:
            # Ratio (tuple like (4,3))
            self.controller.config.ratio = eval(dim_text)

            # Limits: empty => None
            self.controller.config.xlimits = (
                float(xmin_text) if xmin_text else None,
                float(xmax_text) if xmax_text else None,
            )
            self.controller.config.ylimits = (
                float(ymin_text) if ymin_text else None,
                float(ymax_text) if ymax_text else None,
            )

            self.controller.update_plot()
        except Exception:
            # Ignore bad inputs (e.g. partially typed numbers)
            pass

    def open_advanced_dialog(self):
        dlg = AdvancedDialog(self.controller.config, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            dlg.apply_to_config()
            self.controller.update_plot()


    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save plot project", "", "Plot Project (*.pproj *.json)"
        )
        if not path:
            return
        if not (path.endswith(".pproj") or path.endswith(".json")):
            path += ".pproj"
        self.controller.save_project(path)

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open plot project", "", "Plot Project (*.pproj *.json)"
        )
        if not path:
            return

        missing = self.controller.load_project(path)

        # Refresh UI after load
        self.refresh_files_list()
        self.populate_all_columns()
        self.refresh_curve_list()
        if self.controller.curves:
            self.curve_list.setCurrentRow(0)
            self.on_curve_selected(0)

        if missing:
            msg = "Some files were missing and related curves were skipped:\n\n" + "\n".join(
                f"- {k}: {p}" for k, p in missing
            )
            QMessageBox.warning(self, "Missing data files", msg)
