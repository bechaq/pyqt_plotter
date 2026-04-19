from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from Color_modules import PLOTLY_PALETTES, populate_color_combo
from plot_modes import PLOT3D_STYLE_OPTIONS, friendly_plot_mode


class PlotterControlPanel(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.control_layout = QVBoxLayout(self)
        self.control_layout.setContentsMargins(8, 8, 8, 8)
        self.control_layout.setSpacing(10)

        self._build_files_group()
        self._build_view_group()
        self._build_curves_group()
        self._build_project_group()
        self.control_layout.addStretch()

    def _build_files_group(self):
        group = QGroupBox("Files")
        layout = QVBoxLayout(group)

        self.add_file_btn = QPushButton("Add file")
        self.remove_file_btn = QPushButton("Remove selected file")
        layout.addWidget(self.add_file_btn)
        layout.addWidget(self.remove_file_btn)

        self.files_list = QListWidget()
        layout.addWidget(self.files_list)

        layout.addWidget(QLabel("File preview"))
        self.file_preview = QPlainTextEdit()
        self.file_preview.setReadOnly(True)
        self.file_preview.setMaximumBlockCount(40)
        self.file_preview.setPlaceholderText("Select a file to preview its first lines.")
        self.file_preview.setFixedHeight(120)
        layout.addWidget(self.file_preview)

        self.control_layout.addWidget(group)

    def _build_view_group(self):
        group = QGroupBox("View")
        layout = QVBoxLayout(group)

        form = QFormLayout()
        self.plot_mode_value = QLabel(friendly_plot_mode(self.controller.config.plot_mode))
        form.addRow("Plot type", self.plot_mode_value)
        self.dimension_combo = QComboBox()
        self.dimension_combo.addItems([
            "(1,1)", "(1,2)", "(3,4)", "(5,8)",
            "(2,1)", "(4,3)", "(8,5)"
        ])
        form.addRow("Dimension", self.dimension_combo)
        layout.addLayout(form)

        self.subplot_label = QLabel("Subplots")
        self.subplot_list = QListWidget()
        self.subplot_label.setVisible(False)
        self.subplot_list.setVisible(False)
        layout.addWidget(self.subplot_label)
        layout.addWidget(self.subplot_list)

        ticks = QGridLayout()
        ticks.addWidget(QLabel("X ticks", alignment=Qt.AlignCenter), 0, 0)
        ticks.addWidget(QLabel("Y ticks", alignment=Qt.AlignCenter), 0, 1)
        self.z_ticks_label = QLabel("Z ticks", alignment=Qt.AlignCenter)
        ticks.addWidget(self.z_ticks_label, 0, 2)
        self.x_ticks_edit = QSlider(Qt.Horizontal)
        self.x_ticks_edit.setRange(1, 20)
        self.x_ticks_edit.setValue(5)
        self.y_ticks_edit = QSlider(Qt.Horizontal)
        self.y_ticks_edit.setRange(1, 20)
        self.y_ticks_edit.setValue(5)
        self.z_ticks_edit = QSlider(Qt.Horizontal)
        self.z_ticks_edit.setRange(1, 20)
        self.z_ticks_edit.setValue(5)
        ticks.addWidget(self.x_ticks_edit, 1, 0)
        ticks.addWidget(self.y_ticks_edit, 1, 1)
        ticks.addWidget(self.z_ticks_edit, 1, 2)
        self.z_ticks_label.setVisible(False)
        self.z_ticks_edit.setVisible(False)
        layout.addLayout(ticks)

        self.control_layout.addWidget(group)

    def _build_curves_group(self):
        group = QGroupBox("Curves")
        layout = QVBoxLayout(group)

        self.add_curve_btn = QPushButton("Add curve")
        self.remove_curve_btn = QPushButton("Remove selected curve")
        layout.addWidget(self.add_curve_btn)

        self.curve_list = QListWidget()
        layout.addWidget(self.curve_list)
        layout.addWidget(self.remove_curve_btn)

        form = QFormLayout()
        self.curve_name_edit = QLineEdit()
        form.addRow("Curve name", self.curve_name_edit)

        columns = QGridLayout()
        self.x_column_label = QLabel("X column")
        self.y_column_label = QLabel("Y column")
        self.z_column_label = QLabel("Z / value column")
        self.x_combo = QComboBox()
        self.y_combo = QComboBox()
        self.z_combo = QComboBox()
        columns.addWidget(self.x_column_label, 0, 0)
        columns.addWidget(self.y_column_label, 0, 1)
        columns.addWidget(self.z_column_label, 0, 2)
        columns.addWidget(self.x_combo, 1, 0)
        columns.addWidget(self.y_combo, 1, 1)
        columns.addWidget(self.z_combo, 1, 2)
        form.addRow(columns)

        axis_row = QGridLayout()
        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["primary", "secondary"])
        self.subplot_index_combo = QComboBox()
        self.subplot_index_combo.addItems(["0"])
        self.render_style_label = QLabel("3D style")
        self.render_style_combo = QComboBox()
        for style, label, description in PLOT3D_STYLE_OPTIONS:
            self.render_style_combo.addItem(f"{label} - {description}", style)
        self.axis_label = QLabel("Axis")
        self.subplot_index_label = QLabel("Subplot index")
        axis_row.addWidget(self.axis_label, 0, 0)
        axis_row.addWidget(self.subplot_index_label, 0, 1)
        axis_row.addWidget(self.render_style_label, 0, 2)
        axis_row.addWidget(self.axis_combo, 1, 0)
        axis_row.addWidget(self.subplot_index_combo, 1, 1)
        axis_row.addWidget(self.render_style_combo, 1, 2)
        self.render_style_label.setVisible(False)
        self.render_style_combo.setVisible(False)
        form.addRow(axis_row)

        color_row = QGridLayout()
        self.palette_combo = QComboBox()
        self.palette_combo.addItems(PLOTLY_PALETTES.keys())
        self.palette_combo.setCurrentText(self.controller.config.palette_name)
        self.color_combo = QComboBox()
        populate_color_combo(self.color_combo, PLOTLY_PALETTES[self.controller.config.palette_name])
        self.color_combo.setFixedWidth(110)
        self.palette_label = QLabel("Palette")
        self.color_label = QLabel("Curve color")
        color_row.addWidget(self.palette_label, 0, 0)
        color_row.addWidget(self.color_label, 0, 1)
        color_row.addWidget(self.palette_combo, 1, 0)
        color_row.addWidget(self.color_combo, 1, 1)
        form.addRow(color_row)

        layout.addLayout(form)
        self.control_layout.addWidget(group)

    def _build_project_group(self):
        group = QGroupBox("Project")
        layout = QVBoxLayout(group)

        undo_row = QHBoxLayout()
        self.undo_btn = QPushButton("Undo")
        self.redo_btn = QPushButton("Redo")
        undo_row.addWidget(self.undo_btn)
        undo_row.addWidget(self.redo_btn)
        layout.addLayout(undo_row)

        export_row = QHBoxLayout()
        self.export_png_btn = QPushButton("Export PNG")
        self.export_svg_btn = QPushButton("Export SVG")
        self.export_pdf_btn = QPushButton("Export PDF")
        export_row.addWidget(self.export_png_btn)
        export_row.addWidget(self.export_svg_btn)
        export_row.addWidget(self.export_pdf_btn)
        layout.addLayout(export_row)

        self.advanced_btn = QPushButton("Advanced...")
        self.plot_btn = QPushButton("Update plot")
        self.save_project_btn = QPushButton("Save plot project...")
        self.open_project_btn = QPushButton("Open plot project...")
        layout.addWidget(self.advanced_btn)
        layout.addWidget(self.plot_btn)
        layout.addWidget(self.save_project_btn)
        layout.addWidget(self.open_project_btn)

        recent_row = QHBoxLayout()
        self.recent_projects_combo = QComboBox()
        self.recent_projects_combo.setPlaceholderText("Recent projects")
        self.open_recent_btn = QPushButton("Open recent")
        recent_row.addWidget(self.recent_projects_combo, 1)
        recent_row.addWidget(self.open_recent_btn)
        layout.addLayout(recent_row)

        self.control_layout.addWidget(group)
