from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QDialogButtonBox,
    QSpinBox, QCheckBox, QLabel, QLineEdit
)

class AdvancedDialog(QDialog):
    """
    Modal dialog that edits PlotConfig fields.
    It reads initial values from config and writes them back on Accept.
    """
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced parameters")
        self.config = config

        layout = QVBoxLayout(self)

        form = QFormLayout()
        layout.addLayout(form)

        # --- Checkboxes ---
        self.grid_check = QCheckBox("Major grid")
        self.grid_check.setChecked(getattr(config, "grid", True))
        form.addRow(self.grid_check)

        self.minor_ticks_check = QCheckBox("Minor ticks")
        self.minor_ticks_check.setChecked(getattr(config, "minor_ticks", True))
        form.addRow(self.minor_ticks_check)

        self.minor_grid_check = QCheckBox("Minor grid")
        self.minor_grid_check.setChecked(getattr(config, "minor_grid", False))
        form.addRow(self.minor_grid_check)

        self.shared_x_check = QCheckBox("Shared X axis")
        self.shared_x_check.setChecked(getattr(config, "shared_x", False))
        form.addRow(self.shared_x_check)

        self.shared_y_check = QCheckBox("Shared Y axis")
        self.shared_y_check.setChecked(getattr(config, "shared_y", False))
        form.addRow(self.shared_y_check)

        self.legend_check = QCheckBox("Legend")
        self.legend_check.setChecked(getattr(config, "legend", True))
        form.addRow(self.legend_check)

        self.subplot_label = QLabel("Subplots layout (rows, cols):")
        self.subplot_rows = QSpinBox()
        self.subplot_rows.setMinimum(1)
        self.subplot_rows.setValue(self.config.subplot_layout[0])
        self.subplot_cols = QSpinBox()
        self.subplot_cols.setMinimum(1)

        self.subplot_cols.setValue(self.config.subplot_layout[1])
        subplot_layout = QHBoxLayout()
        subplot_layout.addWidget(self.subplot_label)
        subplot_layout.addWidget(self.subplot_rows)
        subplot_layout.addWidget(self.subplot_cols)
        form.addRow(subplot_layout)
        
 
        # Buttons (OK / Cancel)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def get_max_subplot_index(self):
        """Return the maximum subplot index based on current rows and columns."""
        rows = self.subplot_rows.value()
        cols = self.subplot_cols.value()
        return rows * cols - 1
    def apply_to_config(self):
        """Write dialog values back into PlotConfig."""
        
        self.config.grid = bool(self.grid_check.isChecked())
        self.config.minor_ticks = bool(self.minor_ticks_check.isChecked())
        self.config.minor_grid = bool(self.minor_grid_check.isChecked())
        self.config.legend = bool(self.legend_check.isChecked())
        self.config.shared_x = bool(self.shared_x_check.isChecked())
        self.config.shared_y = bool(self.shared_y_check.isChecked())

        # Possibly need to un comment
        self.config.dirty = True  # layout may need refresh

        if self.subplot_cols.value() > 1 or self.subplot_rows.value() > 1:
            self.config.subplots = True
        else:
            self.config.subplots = False

        self.config.subplot_layout = (self.subplot_rows.value(), self.subplot_cols.value())
