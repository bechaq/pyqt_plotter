import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QAbstractItemView

from DataFile import DataFile
from MainWindow import MainWindow
import numpy as np


def close_window(window, app):
    window._autosave_timer.stop()
    window.close()
    window.deleteLater()
    app.processEvents()


class MainWindowFileDefaultTests(unittest.TestCase):
    def test_loading_second_file_selects_that_files_columns(self):
        app = QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            first = tmp_path / "first.txt"
            second = tmp_path / "second.txt"
            first.write_text("time current\n0 1\n1 2\n", encoding="utf-8")
            second.write_text("time voltage\n200 10\n500 20\n", encoding="utf-8")

            with patch.dict(os.environ, {"PYQT_PLOTTER_APPDATA": str(tmp_path / "appdata")}):
                window = MainWindow(prompt_for_mode=False)
                with patch.object(QFileDialog, "getOpenFileName", return_value=(str(first), "")):
                    window.load_file()
                with patch.object(QFileDialog, "getOpenFileName", return_value=(str(second), "")):
                    window.load_file()

                second_key = os.path.abspath(second)
                self.assertEqual(window.x_combo.currentData(Qt.UserRole), (second_key, "time"))
                self.assertEqual(window.y_combo.currentData(Qt.UserRole), (second_key, "voltage"))
                close_window(window, app)

        app.processEvents()

    def test_add_curve_rejects_mismatched_column_lengths_and_falls_back(self):
        app = QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with patch.dict(os.environ, {"PYQT_PLOTTER_APPDATA": str(tmp_path / "appdata")}):
                window = MainWindow(prompt_for_mode=False)
                x_key = str(tmp_path / "x.txt")
                y_key = str(tmp_path / "y.txt")
                window.controller.data_files[x_key] = DataFile(
                    x_key,
                    ["x", "compatible_y"],
                    np.array([[0.0, 10.0], [1.0, 11.0], [2.0, 12.0]]),
                )
                window.controller.data_files[y_key] = DataFile(
                    y_key,
                    ["y"],
                    np.array([[0.0], [1.0], [2.0], [3.0]]),
                )
                window.populate_all_columns()
                window._set_combo_to_column(window.x_combo, x_key, "x")
                window._set_combo_to_column(window.y_combo, y_key, "y")

                with patch.object(QMessageBox, "warning") as warning:
                    window.add_curve()

                self.assertEqual(len(window.controller.curves), 0)
                warning.assert_called_once()
                self.assertEqual(window.x_combo.currentData(Qt.UserRole), (x_key, "x"))
                self.assertEqual(window.y_combo.currentData(Qt.UserRole), (x_key, "compatible_y"))
                close_window(window, app)

        app.processEvents()

    def test_curve_edit_rejects_mismatched_column_lengths_and_reverts_selection(self):
        app = QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with patch.dict(os.environ, {"PYQT_PLOTTER_APPDATA": str(tmp_path / "appdata")}):
                window = MainWindow(prompt_for_mode=False)
                x_key = str(tmp_path / "x.txt")
                y_key = str(tmp_path / "y.txt")
                x_data = DataFile(
                    x_key,
                    ["x", "compatible_y"],
                    np.array([[0.0, 10.0], [1.0, 11.0], [2.0, 12.0]]),
                )
                window.controller.data_files[x_key] = x_data
                window.controller.data_files[y_key] = DataFile(
                    y_key,
                    ["y"],
                    np.array([[0.0], [1.0], [2.0], [3.0]]),
                )
                window.populate_all_columns()
                curve = window.controller.add_curve(
                    x_key,
                    x_data,
                    "x",
                    "compatible_y",
                    "primary",
                    "#1f77b4",
                    x_data_file=x_data,
                    y_data_file=x_data,
                )
                window.refresh_curve_list()
                window.curve_list.setCurrentRow(0)
                window.y_combo.blockSignals(True)
                window._set_combo_to_column(window.y_combo, y_key, "y")
                window.y_combo.blockSignals(False)

                with patch.object(QMessageBox, "warning") as warning:
                    window.on_curve_settings_changed()

                warning.assert_called_once()
                self.assertIs(curve.y_data_file, x_data)
                self.assertEqual(curve.y_col, "compatible_y")
                self.assertEqual(window.x_combo.currentData(Qt.UserRole), (x_key, "x"))
                self.assertEqual(window.y_combo.currentData(Qt.UserRole), (x_key, "compatible_y"))
                close_window(window, app)

        app.processEvents()

    def test_tick_sliders_set_exact_visible_tick_counts(self):
        app = QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with patch.dict(os.environ, {"PYQT_PLOTTER_APPDATA": str(tmp_path / "appdata")}):
                window = MainWindow(prompt_for_mode=False)
                file_key = str(tmp_path / "sample.txt")
                data_file = DataFile(
                    file_key,
                    ["x", "y"],
                    np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0]]),
                )
                window.controller.data_files[file_key] = data_file
                window.populate_all_columns()
                window._set_combo_to_column(window.x_combo, file_key, "x")
                window._set_combo_to_column(window.y_combo, file_key, "y")
                window.add_curve()

                window.x_ticks_edit.setValue(3)
                window.y_ticks_edit.setValue(7)
                app.processEvents()

                axis = window.canvas.axes[0]
                self.assertEqual(window.controller.config.xticksN, 3)
                self.assertEqual(window.controller.config.yticksN, 7)
                self.assertEqual(len(axis.get_xticks()), 3)
                self.assertEqual(len(axis.get_yticks()), 7)
                close_window(window, app)

        app.processEvents()

    def test_curve_list_drag_drop_reorders_controller_and_draw_stack(self):
        app = QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with patch.dict(os.environ, {"PYQT_PLOTTER_APPDATA": str(tmp_path / "appdata")}):
                window = MainWindow(prompt_for_mode=False)
                file_key = str(tmp_path / "sample.txt")
                data_file = DataFile(
                    file_key,
                    ["x", "y"],
                    np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0]]),
                )
                window.controller.data_files[file_key] = data_file

                for index, color in enumerate(["#ff0000", "#00ff00", "#0000ff"], start=1):
                    curve = window.controller.add_curve(
                        file_key,
                        data_file,
                        "x",
                        "y",
                        "primary",
                        color,
                        x_data_file=data_file,
                        y_data_file=data_file,
                    )
                    curve.name = f"Curve {index}"

                window.refresh_curve_list()
                self.assertEqual(window.curve_list.dragDropMode(), QAbstractItemView.InternalMove)

                moved = window.curve_list.takeItem(2)
                window.curve_list.insertItem(0, moved)
                window.on_curve_rows_reordered_from_list()

                self.assertEqual(
                    [curve.name for curve in window.controller.curves],
                    ["Curve 3", "Curve 1", "Curve 2"],
                )
                window.controller.update_plot()
                self.assertGreater(
                    window.controller.curves[0]._mpl_line.get_zorder(),
                    window.controller.curves[-1]._mpl_line.get_zorder(),
                )
                close_window(window, app)

        app.processEvents()

    def test_curve_opacity_slider_updates_model_artist_and_project_state(self):
        app = QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with patch.dict(os.environ, {"PYQT_PLOTTER_APPDATA": str(tmp_path / "appdata")}):
                window = MainWindow(prompt_for_mode=False)
                file_key = str(tmp_path / "sample.txt")
                data_file = DataFile(
                    file_key,
                    ["x", "y"],
                    np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0]]),
                )
                window.controller.data_files[file_key] = data_file
                window.populate_all_columns()
                window._set_combo_to_column(window.x_combo, file_key, "x")
                window._set_combo_to_column(window.y_combo, file_key, "y")
                window.add_curve()
                window.curve_list.setCurrentRow(0)

                window.opacity_slider.setValue(35)
                app.processEvents()

                curve = window.controller.curves[0]
                self.assertAlmostEqual(curve.opacity, 0.35)
                self.assertAlmostEqual(curve._mpl_line.get_alpha(), 0.35)
                self.assertAlmostEqual(window.controller.to_dict()["curves"][0]["opacity"], 0.35)
                close_window(window, app)

        app.processEvents()


if __name__ == "__main__":
    unittest.main()
