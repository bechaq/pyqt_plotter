# Curve Order, Opacity, And Exact Ticks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make tick controls exact, add drag/drop curve ordering, and expose per-curve opacity.

**Architecture:** Keep UI state in `MainWindow` and `PlotterControlPanel`, plot state in `Curve` and `AppController`, and rendering behavior in `PlotCanvas`. The curve list order remains the controller order, while `PlotCanvas` uses z-order so top list rows appear above lower rows.

**Tech Stack:** Python, PyQt5, Matplotlib, unittest.

---

### Task 1: Regression Tests

**Files:**
- Modify: `tests/test_mainwindow_file_defaults.py`

- [x] **Step 1: Write failing tests for exact ticks, drag reorder, draw stack, and opacity**

Add tests that create an offscreen `MainWindow`, add sample `DataFile` objects, then assert exact tick counts, `QAbstractItemView.InternalMove`, controller order after list reorder, top-curve z-order, opacity model value, artist alpha, and project serialization.

- [x] **Step 2: Run focused tests to verify they fail**

Run: `python -m unittest tests.test_mainwindow_file_defaults.MainWindowFileDefaultTests.test_tick_sliders_set_exact_visible_tick_counts tests.test_mainwindow_file_defaults.MainWindowFileDefaultTests.test_curve_list_drag_drop_reorders_controller_and_draw_stack tests.test_mainwindow_file_defaults.MainWindowFileDefaultTests.test_curve_opacity_slider_updates_model_artist_and_project_state`

Expected: FAIL because current tick locators are approximate, drag/drop is disabled, and `opacity_slider` does not exist.

### Task 2: Exact Tick Locators

**Files:**
- Modify: `PlotCanvas.py`

- [x] **Step 1: Add an exact locator helper**

Import `LinearLocator` and create `_apply_major_locator(axis_obj, tick_count)` that uses `LinearLocator(numticks=max(1, int(tick_count)))`.

- [x] **Step 2: Replace X/Y/Z tick locator calls**

Use the helper in line, heatmap, 3D, and secondary-axis rendering wherever slider-derived tick counts are applied.

- [x] **Step 3: Run the focused tick test**

Run: `python -m unittest tests.test_mainwindow_file_defaults.MainWindowFileDefaultTests.test_tick_sliders_set_exact_visible_tick_counts`

Expected: PASS.

### Task 3: Drag/Drop Curve Ordering

**Files:**
- Modify: `PlotterControlPanel.py`
- Modify: `MainWindow.py`
- Modify: `PlotCanvas.py`

- [x] **Step 1: Enable internal move drag/drop**

Set `self.curve_list` to `QAbstractItemView.InternalMove`, move action, single selection, and a visible drop indicator.

- [x] **Step 2: Store curve objects on list items**

In `MainWindow.refresh_curve_list`, create `QListWidgetItem`, set the display text, and store the corresponding curve object in `Qt.UserRole`.

- [x] **Step 3: Rebuild controller order after rows move**

Connect the list model `rowsMoved` signal to `on_curve_rows_reordered_from_list`. The handler rebuilds `controller.curves` from item data, updates the plot, and finalizes undo/dirty state.

- [x] **Step 4: Apply z-order from list order**

In `PlotCanvas`, compute z-order as `len(curves) - index` and apply it to artists so the top list item has the highest z-order.

- [x] **Step 5: Run the focused drag/order test**

Run: `python -m unittest tests.test_mainwindow_file_defaults.MainWindowFileDefaultTests.test_curve_list_drag_drop_reorders_controller_and_draw_stack`

Expected: PASS.

### Task 4: Curve Opacity

**Files:**
- Modify: `Curves.py`
- Modify: `AppController.py`
- Modify: `PlotterControlPanel.py`
- Modify: `MainWindow.py`
- Modify: `PlotCanvas.py`

- [x] **Step 1: Add model and persistence**

Add `opacity=1.0` to `Curve`, `AppController.add_curve`, `AppController.update_curve`, `to_dict`, and `_make_curve_from_dict`.

- [x] **Step 2: Add opacity UI**

Add `opacity_slider` in `PlotterControlPanel` with range `0..100` and default `100`. Bind it in `MainWindow._bind_control_attrs`, block/sync it in `on_curve_selected`, and send slider value divided by 100 through add/update curve paths.

- [x] **Step 3: Apply alpha in renderers**

Apply opacity to 2D line `alpha`, heatmap artists, 3D line artists, surface alpha, scatter fallbacks, volume facecolors/fallbacks, and representative legend patches.

- [x] **Step 4: Run the focused opacity test**

Run: `python -m unittest tests.test_mainwindow_file_defaults.MainWindowFileDefaultTests.test_curve_opacity_slider_updates_model_artist_and_project_state`

Expected: PASS.

### Task 5: Full Verification

**Files:**
- Test-only

- [x] **Step 1: Run all unit tests**

Run: `python -m unittest discover -s tests`

Expected: all tests pass.

- [x] **Step 2: Run manual regression script**

Run: `python tmp\manual_regression_test.py`

Expected: `manual_regression_test: OK`.

- [x] **Step 3: Run offscreen smoke against the requested Z data**

Run an offscreen `MainWindow` load of `Z:\A24\Transfo\Full wave rectifier\Inductive_switching\Tout_debut.txt`, add a curve, change tick sliders and opacity, and assert the file still loads from `200.0` to `500.0`.

Expected: smoke script exits with code 0 and prints the measured config/artist values.
