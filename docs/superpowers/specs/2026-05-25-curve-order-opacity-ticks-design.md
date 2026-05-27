# Curve Order, Opacity, And Exact Ticks Design

## Goal

Make the tick sliders visibly deterministic, allow curve stacking order to be controlled from the curve list, and add per-curve opacity.

## Requirements

- X, Y, and Z tick sliders should set the exact number of visible major ticks requested by the slider.
- The curve list should support drag-and-drop reordering. Up/down buttons are out of scope unless drag-and-drop cannot be made reliable.
- The top curve in the curve list should be visually on top of lower curves.
- Curves should have an opacity parameter exposed as a 0-100 percent slider, defaulting to 100 percent for existing curves and projects.
- Opacity should persist in project files and apply to line plots, heatmaps, 3D lines, surfaces, volume fallbacks, and legend representatives where the renderer exposes alpha control.

## Design

- Replace approximate `MaxNLocator` slider behavior with `LinearLocator(numticks=N)` through a small PlotCanvas helper.
- Keep `controller.curves` in the same top-to-bottom order shown in the `QListWidget`.
- Enable `QListWidget` internal drag/drop and rebuild `controller.curves` from each item's stored curve object after rows move.
- Use explicit artist `zorder` values so earlier list rows draw above later list rows without reversing legend order.
- Add `Curve.opacity`, serialize it in `AppController`, bind it to an `opacity_slider` in `PlotterControlPanel`, and route updates through the existing curve settings handler.

## Test Strategy

- Add failing tests for exact tick counts, drag-drop list reorder, z-order stacking, opacity model update, opacity artist alpha, and project serialization.
- Keep the existing unittest suite and manual regression script passing.
