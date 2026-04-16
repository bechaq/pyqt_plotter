import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QFileDialog

from DataFile import load_data_file
from Helpers import detect_delimiter
from MainWindow import MainWindow


def write_text(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    app = QApplication.instance() or QApplication([])

    sample = "Column1 Column2\n1 2\n3 4\n"
    decimal_comma = "X Y\n1,23 4,56\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        run1 = root / "run1"
        run2 = root / "run2"
        run1.mkdir()
        run2.mkdir()

        file1 = run1 / "results.txt"
        file2 = run2 / "results.txt"
        decimal_file = root / "decimal_space.txt"

        write_text(file1, sample)
        write_text(file2, sample)
        write_text(decimal_file, decimal_comma)

        window = MainWindow()

        original_picker = QFileDialog.getOpenFileName
        paths = iter([(str(file1), ""), (str(file2), "")])
        QFileDialog.getOpenFileName = staticmethod(lambda *args, **kwargs: next(paths))
        try:
            window.load_file()
            window.load_file()
        finally:
            QFileDialog.getOpenFileName = original_picker

        assert_true(len(window.controller.data_files) == 2, "Duplicate basenames should not overwrite each other")
        labels = [window.files_list.item(i).text() for i in range(window.files_list.count())]
        assert_true(labels[0] != labels[1], "Duplicate basenames should display distinct labels")

        window._set_combo_to_column(window.x_combo, os.path.abspath(file1), "Column1")
        window._set_combo_to_column(window.y_combo, os.path.abspath(file1), "Column2")
        window.add_curve()
        assert_true(len(window.controller.curves) == 1, "Expected one curve after add_curve")

        window.curve_list.setCurrentRow(0)
        window.on_curve_selected(0)
        window._set_combo_to_column(window.y_combo, os.path.abspath(file2), "Column2")
        window.on_curve_settings_changed()
        window.controller.remove_file(os.path.abspath(file2))
        assert_true(len(window.controller.curves) == 0, "Removing a referenced Y-source file should remove dependent curves")

        window.controller.data_files.clear()
        window.controller.curves.clear()
        df = load_data_file(str(file1))
        window.controller.data_files[os.path.abspath(file1)] = df
        curve = window.controller.add_curve(
            os.path.abspath(file1),
            df,
            "Column1",
            "Column2",
            "primary",
            "#000000",
            x_data_file=df,
            y_data_file=df,
        )
        curve.subplot_index = 4
        window.controller.config.subplot_layout = (1, 1)
        window.controller.normalize_curve_subplots()
        assert_true(curve.subplot_index == 0, "normalize_curve_subplots should clamp invalid subplot indices")

        window.controller.config.subplots_config = {0: {"xlim": (0.5, 3.5), "ylim": (1.5, 4.5)}}
        window.controller.config.xlimits = (0.5, 3.5)
        window.controller.config.ylimits = (1.5, 4.5)
        window.controller.config.minor_ticks = True
        window.controller.config.minor_grid = False
        window.controller.update_plot()
        first_xlim = tuple(round(v, 3) for v in window.canvas.axes[0].get_xlim())
        first_ylim = tuple(round(v, 3) for v in window.canvas.axes[0].get_ylim())
        window.controller.update_plot()
        second_xlim = tuple(round(v, 3) for v in window.canvas.axes[0].get_xlim())
        second_ylim = tuple(round(v, 3) for v in window.canvas.axes[0].get_ylim())
        assert_true(first_xlim == (0.5, 3.5) and second_xlim == (0.5, 3.5), "Configured x limits should persist across redraws")
        assert_true(first_ylim == (1.5, 4.5) and second_ylim == (1.5, 4.5), "Configured y limits should persist across redraws")
        assert_true(len(window.canvas.axes[0].xaxis.get_minorticklocs()) > 0, "Minor ticks should remain enabled when minor grid is off")

        decimal_df = load_data_file(str(decimal_file))
        assert_true(detect_delimiter("1,23 4,56") is None, "Whitespace-delimited decimal comma rows should not be treated as CSV")
        assert_true(decimal_df.data.shape == (1, 2), "Decimal-comma whitespace data should load as two columns")

        print("manual_regression_test: OK")

    app.quit()


if __name__ == "__main__":
    main()
