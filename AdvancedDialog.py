from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QDialogButtonBox,
    QSpinBox, QCheckBox
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
        self.minor_ticks_check.setChecked(getattr(config, "minor_ticks", False))
        form.addRow(self.minor_ticks_check)

        self.minor_grid_check = QCheckBox("Minor grid")
        self.minor_grid_check.setChecked(getattr(config, "minor_grid", False))
        form.addRow(self.minor_grid_check)

        self.legend_check = QCheckBox("Legend")
        self.legend_check.setChecked(getattr(config, "legend", True))
        form.addRow(self.legend_check)

        # Buttons (OK / Cancel)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply_to_config(self):
        """Write dialog values back into PlotConfig."""
        
        self.config.grid = bool(self.grid_check.isChecked())
        self.config.minor_ticks = bool(self.minor_ticks_check.isChecked())
        self.config.minor_grid = bool(self.minor_grid_check.isChecked())
        self.config.legend = bool(self.legend_check.isChecked())
        self.config.dirty = True  # layout may need refresh
