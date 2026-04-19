from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from plot_modes import PLOT_MODE_OPTIONS


class PlotModeDialog(QDialog):
    def __init__(self, current_mode="line2d", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose plot type")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the kind of plot you want to start with."))

        self.mode_combo = QComboBox()
        for mode, label, description in PLOT_MODE_OPTIONS:
            self.mode_combo.addItem(f"{label} - {description}", mode)
        index = self.mode_combo.findData(current_mode)
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)
        layout.addWidget(self.mode_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_mode(self):
        return self.mode_combo.currentData()

    @classmethod
    def choose(cls, current_mode="line2d", parent=None):
        dialog = cls(current_mode=current_mode, parent=parent)
        if dialog.exec_() == QDialog.Accepted:
            return dialog.selected_mode()
        return None
