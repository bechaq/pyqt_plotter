import os
import tempfile
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt5.QtWidgets import QApplication, QFileDialog

from DataFile import load_data_file
from Helpers import detect_delimiter
from MainWindow import MainWindow


def write_text(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def curve_summary(window):
    return [
        (
            c.name,
            c.axis,
            c.x_col,
            c.y_col,
            c.z_col,
            c.render_style,
            os.path.basename(c.x_data_file.path),
            os.path.basename(c.y_data_file.path),
            os.path.basename(c.z_data_file.path) if c.z_data_file is not None else None,
            c.subplot_index,
        )
        for c in window.controller.curves
    ]


def find_named_attr(obj, *names):
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def project_roundtrip(window, project_path: Path):
    window.controller.save_project(str(project_path))
    assert_true(project_path.exists(), "Expected autosave/project snapshot file to be written")
    assert_true(project_path.stat().st_size > 0, "Saved project snapshot should not be empty")

    clone = MainWindow(prompt_for_mode=False)
    try:
        missing = clone.controller.load_project(str(project_path))
        assert_true(not missing, f"Project roundtrip should not report missing files: {missing}")
        assert_true(
            clone.controller.config.plot_mode == window.controller.config.plot_mode,
            "Saved project should preserve plot mode",
        )
        assert_true(
            clone.controller.config.zticksN == window.controller.config.zticksN,
            "Saved project should preserve 3D Z tick settings",
        )
        assert_true(
            curve_summary(clone) == curve_summary(window),
            "Saved project should round-trip curve state for autosave validation",
        )
        return clone
    except Exception:
        clone.close()
        raise


def exercise_undo_redo_if_available(window):
    undo_action = find_named_attr(window, "undo_action", "actionUndo", "undoAction")
    redo_action = find_named_attr(window, "redo_action", "actionRedo", "redoAction")
    undo_stack = find_named_attr(window, "undo_stack", "command_stack")
    undo_method = find_named_attr(window, "undo")
    redo_method = find_named_attr(window, "redo")

    if undo_action is None and redo_action is None and undo_stack is None and undo_method is None and redo_method is None:
        print("undo/redo API not exposed yet; skipped optional smoke check")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        baseline_path = Path(tmpdir) / "undo_baseline.pproj"
        window.controller.save_project(str(baseline_path))
        before = curve_summary(window)

        if undo_action is not None and redo_action is not None:
            window.curve_list.setCurrentRow(0)
            window.on_curve_selected(0)
            window.add_curve()
            after_add = curve_summary(window)
            assert_true(after_add != before, "Undo/redo smoke setup should change the curve state")

            undo_action.trigger()
            window.controller.update_plot()
            app = QApplication.instance()
            if app is not None:
                app.processEvents()
            after_undo = curve_summary(window)
            assert_true(
                after_undo == before,
                "Undo action should restore the previous curve state",
            )

            redo_action.trigger()
            window.controller.update_plot()
            if app is not None:
                app.processEvents()
            after_redo = curve_summary(window)
            assert_true(
                after_redo != before,
                "Redo action should restore the undone change",
            )
        elif undo_method is not None and redo_method is not None:
            window.curve_list.setCurrentRow(0)
            window.on_curve_selected(0)
            window.add_curve()
            after_add = curve_summary(window)
            assert_true(after_add != before, "Undo/redo smoke setup should change the curve state")
            undo_method()
            app = QApplication.instance()
            if app is not None:
                app.processEvents()
            assert_true(curve_summary(window) == before, "Undo method should restore the previous curve state")
            redo_method()
            if app is not None:
                app.processEvents()
            assert_true(curve_summary(window) != before, "Redo method should restore the undone change")
        else:
            print("undo/redo stack present but no standard QAction hooks found; skipped action smoke check")

        window.controller.load_project(str(baseline_path))
        window.controller.update_plot()


def main():
    app = QApplication.instance() or QApplication([])

    sample = "Column1 Column2\n1 2\n3 4\n"
    decimal_comma = "X Y\n1,23 4,56\n"
    xyz_sample = "X Y Z\n0 0 1\n0 1 2\n1 0 3\n1 1 4\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        os.environ["PYQT_PLOTTER_APPDATA"] = str(root / "appdata")
        run1 = root / "run1"
        run2 = root / "run2"
        run1.mkdir()
        run2.mkdir()

        file1 = run1 / "results.txt"
        file2 = run2 / "results.txt"
        decimal_file = root / "decimal_space.txt"
        xyz_file = root / "xyz_points.txt"

        write_text(file1, sample)
        write_text(file2, sample)
        write_text(decimal_file, decimal_comma)
        write_text(xyz_file, xyz_sample)

        window = MainWindow(prompt_for_mode=False)

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
        summary_before_undo = curve_summary(window)
        window.undo()
        assert_true(len(window.controller.curves) == 0, "Undo should remove the added curve")
        window.redo()
        assert_true(curve_summary(window) == summary_before_undo, "Redo should restore the removed curve")

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

        window.controller.curves.clear()
        window.controller.config.subplot_layout = (1, 1)
        window.controller.add_curve(
            os.path.abspath(file1),
            df,
            "Column1",
            "Column2",
            "secondary",
            "#ff0000",
            x_data_file=df,
            y_data_file=df,
        )
        window.controller.add_curve(
            os.path.abspath(file1),
            df,
            "Column1",
            "Column2",
            "secondary",
            "#00ff00",
            x_data_file=df,
            y_data_file=df,
        )
        assert_true(len(window.canvas.ax2) == 1, "Only one secondary axis should be created per subplot")
        assert_true(len(window.canvas.fig.axes) == 2, "Figure should contain one primary and one secondary axis, not extra twins")
        app.processEvents()
        secondary = window.canvas.ax2[0]
        sec_labels = [label.get_text() for label in secondary.get_yticklabels()]
        assert_true(tuple(round(v, 3) for v in secondary.get_ylim()) != (0.0, 1.0), "Secondary axis should not fall back to unit-interval limits")
        assert_true(not {"0.0", "0.2", "0.4", "0.6", "0.8", "1.0"}.intersection(sec_labels), "Secondary axis should not show default unit-interval tick labels")

        decimal_df = load_data_file(str(decimal_file))
        assert_true(detect_delimiter("1,23 4,56") is None, "Whitespace-delimited decimal comma rows should not be treated as CSV")
        assert_true(decimal_df.data.shape == (1, 2), "Decimal-comma whitespace data should load as two columns")

        xyz_df = load_data_file(str(xyz_file))
        xyz_key = os.path.abspath(xyz_file)
        window.controller.data_files.clear()
        window.controller.curves.clear()
        window.controller.data_files[xyz_key] = xyz_df
        window.controller.config.plot_mode = "heatmap2d"
        window._apply_plot_mode_ui()
        heatmap_color_mode = window.color_mode_combo.findData("colormap")
        if heatmap_color_mode >= 0:
            window.color_mode_combo.setCurrentIndex(heatmap_color_mode)
        window.show_colorbar_checkbox.setChecked(True)
        assert_true(window.z_ticks_edit.isHidden(), "Heatmap mode should keep the Z tick control hidden")
        window.refresh_files_list()
        window.populate_all_columns()
        window._set_combo_to_column(window.x_combo, xyz_key, "X")
        window._set_combo_to_column(window.y_combo, xyz_key, "Y")
        window._set_combo_to_column(window.z_combo, xyz_key, "Z")
        window.add_curve()
        assert_true(len(window.controller.curves) == 1, "Heatmap mode should add one plot item")
        assert_true(window.controller.curves[0].z_col == "Z", "Heatmap mode should persist the selected Z column")
        window.controller.update_plot()
        assert_true(len(window.canvas._colorbars) == 1, "Heatmap mode should create a colorbar")
        heatmap_clone = project_roundtrip(window, root / "heatmap_roundtrip.pproj")
        heatmap_clone.close()

        window.controller.curves.clear()
        window.controller.config.plot_mode = "plot3d"
        window._apply_plot_mode_ui()
        assert_true(not window.z_ticks_edit.isHidden(), "3D mode should show the Z tick control")
        window.populate_all_columns()
        window._set_combo_to_column(window.x_combo, xyz_key, "X")
        window._set_combo_to_column(window.y_combo, xyz_key, "Y")
        window._set_combo_to_column(window.z_combo, xyz_key, "Z")
        line_idx = window.render_style_combo.findData("line")
        assert_true(line_idx >= 0, "3D style combo should include line")
        window.render_style_combo.setCurrentIndex(line_idx)
        window.add_curve()
        window.controller.update_plot()
        assert_true(getattr(window.canvas.axes[0], "name", "") == "3d", "3D mode should create 3D axes")
        assert_true(hasattr(window.canvas.axes[0], "zaxis"), "3D mode should expose a Z axis")
        window.z_ticks_edit.setValue(9)
        window.on_canvas_settings_changed()
        assert_true(window.controller.config.zticksN == 9, "Z tick control should update the 3D config")
        assert_true(
            window.canvas.axes[0].zaxis.get_major_locator().__class__.__name__ == "LinearLocator",
            "3D Z axis should use an exact-count LinearLocator",
        )
        assert_true(len(window.canvas.axes[0].get_zticks()) == 9, "Z tick control should apply exactly 9 visible ticks")
        plot3d_clone = project_roundtrip(window, root / "plot3d_roundtrip.pproj")
        plot3d_clone.close()

        window.controller.curves.clear()
        surface_idx = window.render_style_combo.findData("surface")
        assert_true(surface_idx >= 0, "3D style combo should include surface")
        window.render_style_combo.setCurrentIndex(surface_idx)
        solid_mode_idx = window.color_mode_combo.findData("solid")
        assert_true(solid_mode_idx >= 0, "Color mode combo should include solid color")
        window.color_mode_combo.setCurrentIndex(solid_mode_idx)
        window.add_curve()
        window.controller.update_plot()
        assert_true(window.controller.curves[0].render_style == "surface", "Surface mode should persist the chosen render style")
        assert_true(window.controller.curves[0].uses_colormap is False, "Surface mode should support a solid-color render mode")
        assert_true(window.controller.curves[0].show_colorbar is False, "Solid-color surfaces should not force a colorbar")
        assert_true(len(window.canvas._colorbars) == 0, "Solid-color surfaces should not create a colorbar")
        assert_true(len(window.canvas.axes[0].collections) > 0, "Surface mode should draw a 3D collection")
        surface_clone = project_roundtrip(window, root / "surface_roundtrip.pproj")
        surface_clone.close()

        window.controller.curves.clear()
        volume_idx = window.render_style_combo.findData("volume")
        assert_true(volume_idx >= 0, "3D style combo should include volume")
        window.render_style_combo.setCurrentIndex(volume_idx)
        colormap_mode_idx = window.color_mode_combo.findData("colormap")
        window.color_mode_combo.setCurrentIndex(colormap_mode_idx)
        window.show_colorbar_checkbox.setChecked(True)
        window.add_curve()
        window.controller.update_plot()
        assert_true(window.controller.curves[0].render_style == "volume", "Volume mode should persist the chosen render style")
        assert_true(len(window.canvas._colorbars) >= 1, "Volume mode should add a colorbar")
        volume_clone = project_roundtrip(window, root / "volume_roundtrip.pproj")
        volume_clone.close()

        assert_true(hasattr(window, "workspace_splitter"), "Workspace should expose a draggable splitter")
        assert_true(window.workspace_splitter.count() == 2, "Workspace splitter should contain left controls and right plot area")

        window.controller.curves.clear()
        window.render_style_combo.setCurrentIndex(surface_idx)
        window.color_mode_combo.setCurrentIndex(colormap_mode_idx)
        window.show_colorbar_checkbox.setChecked(True)
        window.add_curve()
        boxes = []
        colorbar_boxes = []
        for _ in range(4):
            window.controller.update_plot()
            plot_box = window.canvas.axes[0].get_position()
            boxes.append(tuple(round(v, 4) for v in (plot_box.x0, plot_box.y0, plot_box.x1, plot_box.y1)))
            assert_true(len(window.canvas._colorbars) == 1, "Repeated 3D redraws should preserve exactly one colorbar")
            cb_ax = window.canvas._colorbars[0].ax
            cb_box = cb_ax.get_position()
            colorbar_boxes.append(tuple(round(v, 4) for v in (cb_box.x0, cb_box.y0, cb_box.x1, cb_box.y1)))
        assert_true(len(set(boxes)) == 1, "Repeated redraws should not keep shrinking the main plot axes")
        plot_box = window.canvas.axes[0].get_position()
        cb_box = window.canvas._colorbars[0].ax.get_position()
        assert_true((cb_box.x1 - cb_box.x0) < (plot_box.x1 - plot_box.x0) * 0.2, "Colorbar should stay visually narrower than the main plot")

        exercise_undo_redo_if_available(window)

        autosave_path = root / "autosave_roundtrip.pproj"
        autosave_clone = project_roundtrip(window, autosave_path)
        autosave_clone.close()

        window._write_autosave()
        autosave_payload = window.state_store.load_autosave()
        assert_true(autosave_payload is not None, "Dirty state should produce an autosave payload")
        restored = MainWindow(prompt_for_mode=False)
        restored._restore_state(autosave_payload["project_state"], mark_dirty=True)
        assert_true(curve_summary(restored) == curve_summary(window), "Autosave restore should rebuild the same curve state")
        restored.close()

        print("manual_regression_test: OK")

    app.quit()


if __name__ == "__main__":
    main()
