# Plot Mode Validation Matrix

Scope: adding a startup plot-mode picker and supporting multiple render modes such as 2D line, 2D heatmap, and 3D plots.

## Shared Startup Flow
- App launches without a project loaded.
- Mode picker is shown before the main window or as the first step inside it.
- Selected mode persists only for the current session unless you intentionally store a default.
- Closing the picker without selection is handled cleanly.

## 2D Line Mode
- Existing behavior still opens as expected.
- File loading, curve editing, save/load, undo/redo, autosave, and recent projects still work.
- Secondary axis, subplot layout, shared axes, and legend behavior remain unchanged.
- Existing regression checks continue to pass.

## 2D Heatmap Mode
- Loading a single 2D array or x/y/z grid displays a heatmap correctly.
- Colorbar appears and updates when the data changes.
- Axis labels, limits, and subplot layout behave consistently with the selected data shape.
- Saving and reloading preserve the heatmap-specific state.
- Export produces a visually correct raster/vector output.

## 3D Mode
- 3D axes are created correctly and do not regress the 2D canvas.
- Rotation/interaction works and redraws do not reset the view unexpectedly.
- Labels, limits, and legends are either supported or clearly disabled.
- Save/load preserves the plot mode and 3D-specific camera/view settings if supported.
- Export produces a readable image of the 3D plot.

## Mode Switching / Guard Rails
- A 2D-only project cannot be opened in a 3D-only renderer without a clear fallback or conversion path.
- Unsupported controls are hidden or disabled per mode.
- Autosave restores into the same plot mode that created it.
- Undo/redo does not mix commands across incompatible modes.
- Recent projects remember the mode used when the project was saved.

## Recommended Regression Order
1. Confirm the current 2D line path still passes all existing tests.
2. Add one smoke test for mode selection at startup.
3. Add one smoke test per new mode for load, edit, export, and restore.
4. Add one cross-mode persistence test for save/load/autosave.
5. Add one guard-rail test for invalid or unsupported mode transitions.
