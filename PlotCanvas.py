from Color_modules import PLOTLY_PALETTES
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.ticker import AutoMinorLocator, MaxNLocator
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import numpy as np

class PlotCanvas(FigureCanvas):
    def __init__(self):
        self.fig = Figure()
        self.axes = []
        self.ax2 = {}          # secondary axes per subplot
        self._colorbars = []
        self._last_layout = None
        self._last_shared_x = None
        self._last_shared_y = None
        self._last_plot_mode = None
        super().__init__(self.fig)
        
    def clear(self, layout, config):
        need_rebuild = (
            self._last_layout != layout
            or self._last_shared_x != config.shared_x
            or self._last_shared_y != config.shared_y
            or self._last_plot_mode != getattr(config, "plot_mode", "line2d")
        )

        if need_rebuild:
            self._create_subplots(layout, config.shared_x, config.shared_y, config)
            self._last_layout = layout
            self._last_shared_x = config.shared_x
            self._last_shared_y = config.shared_y
            self._last_plot_mode = getattr(config, "plot_mode", "line2d")
            
        else:
            for ax in self.axes:
                ax.clear()
            for ax2 in self.ax2.values():
                ax2.remove()
            self.ax2.clear()
            self._remove_colorbars()


    def ratio_to_inches(self, ratio):
        Max_x = self.width()/self.fig.get_dpi() 
        Max_y = self.height()/self.fig.get_dpi() 
       

        if ratio[0] > ratio[1]:
            base_size = min(Max_x, ratio[0] * Max_y / ratio[1])
            return base_size, base_size * ratio[1] / ratio[0]
        else:
            base_size = min(Max_y, ratio[1] * Max_x / ratio[0])
            return base_size * ratio[0] / ratio[1], base_size
        

    def draw_curves(self, curves, config):
        self.clear(config.subplot_layout, config)

        plot_mode = getattr(config, "plot_mode", "line2d")
        if plot_mode == "heatmap2d":
            self._draw_heatmaps(curves, config)
        elif plot_mode == "plot3d":
            self._draw_3d(curves, config)
        else:
            self._draw_lines(curves, config)

        rows, _ = config.subplot_layout
        w, h = self.ratio_to_inches(config.ratio)
        self.fig.set_size_inches(w, h)

        if config.dirty:
            if plot_mode == "line2d" and config.shared_x and rows > 1:
                self.fig.subplots_adjust(hspace=0)
            else:
                self.fig.tight_layout()
            config.dirty = False

        self.draw_idle()


    # def _get_axis(self, axis):

    #     if axis == "primary":
    #         return self.ax
    #     elif axis == "secondary":
    #         if self.ax2 is None:
    #             self.ax2 = self.ax.twinx()
    #         return self.ax2
    #     else:
    #         raise ValueError("Unknown axis")
    
    def _draw_lines(self, curves, config):
        max_index = max(0, len(self.axes) - 1)
        for curve in curves:
            i = self._normalized_subplot_index(curve, max_index)
            ax = self.axes[i]

            if curve.axis == "secondary":
                secondary_ax = self.ax2.get(i)
                if secondary_ax is None:
                    secondary_ax = ax.twinx()
                    self.ax2[i] = secondary_ax
                ax = secondary_ax

            x, y = curve.xy()
            (line,) = ax.plot(
                x,
                y,
                label=curve.label,
                color=curve.color,
                marker=curve.marker,
                markersize=curve.marker_size,
                markerfacecolor=curve.marker_face_color,
                markeredgecolor=curve.marker_edge_color,
                linestyle=curve.linestyle,
                linewidth=curve.linewidth,
            )
            curve._mpl_line = line

        for secondary_ax in self.ax2.values():
            secondary_ax.relim()
            secondary_ax.autoscale_view(scalex=False, scaley=True)

        for i, ax in enumerate(self.axes):
            ov = config.subplots_config.get(i, {})
            rows, cols = config.subplot_layout
            r, _ = divmod(i, cols)
            ax2 = self.ax2.get(i)

            if config.shared_x:
                if r == rows - 1:
                    ax.set_xlabel(ov.get("xlabel", config.xlabel))
                else:
                    ax.set_xlabel("")
                    ax.tick_params(labelbottom=False)
            else:
                ax.set_xlabel(ov.get("xlabel", config.xlabel))

            xlim = ov.get("xlim", config.xlimits) or config.xlimits
            ylim = ov.get("ylim", config.ylimits) or config.ylimits
            xticks = ov.get("xticksN", config.xticksN) or config.xticksN
            yticks = ov.get("yticksN", config.yticksN) or config.yticksN

            ax.set_ylabel(ov.get("ylabel", config.ylabel))
            if xlim is not None:
                ax.set_xlim(xlim)
            if ylim is not None:
                ax.set_ylim(ylim)
            if xticks is not None:
                ax.xaxis.set_major_locator(MaxNLocator(xticks))
            if yticks is not None:
                ax.yaxis.set_major_locator(MaxNLocator(yticks))

            if rows > 1 and config.shared_x and r > 0:
                yticks_labels = ax.get_yticklabels()
                if yticks_labels:
                    yticks_labels[-1].set_visible(False)

            self._apply_minor_ticks(ax, config.minor_ticks)
            ax.grid(config.grid, which="major")
            if config.minor_grid:
                ax.grid(True, which="minor", linestyle=":", linewidth=0.5)
            else:
                ax.grid(False, which="minor")

            if ax2 is not None:
                ax2.yaxis.set_ticks_position("right")
                ax2.yaxis.set_label_position("right")
                ax2.tick_params(
                    axis="y",
                    which="both",
                    left=False,
                    labelleft=False,
                    right=True,
                    labelright=True,
                )
                if yticks is not None:
                    ax2.yaxis.set_major_locator(MaxNLocator(yticks))
                self._apply_minor_ticks(ax2, config.minor_ticks, include_x=False)
                ax2.grid(False, which="both")

            if config.legend:
                handles, labels = ax.get_legend_handles_labels()
                if ax2 is not None:
                    handles2, labels2 = ax2.get_legend_handles_labels()
                    handles += handles2
                    labels += labels2
                if handles:
                    legend = ax.legend(handles, labels)
                    legend.set_draggable(True)

    def _draw_heatmaps(self, curves, config):
        max_index = max(0, len(self.axes) - 1)
        subplot_artists = {}
        subplot_labels = {}

        for curve in curves:
            i = self._normalized_subplot_index(curve, max_index)
            ax = self.axes[i]
            x, y, z = curve.xyz()
            if z is None:
                continue

            cmap = self._colormap_for_curve(curve)
            try:
                if len(x) >= 3:
                    artist = ax.tripcolor(x, y, z, shading="auto", cmap=cmap)
                else:
                    artist = ax.scatter(x, y, c=z, cmap=cmap)
            except Exception:
                artist = ax.scatter(x, y, c=z, cmap=cmap)

            subplot_artists[i] = artist
            subplot_labels[i] = curve.z_col or curve.name or "Value"

        for i, ax in enumerate(self.axes):
            ov = config.subplots_config.get(i, {})
            rows, cols = config.subplot_layout
            r, _ = divmod(i, cols)

            if config.shared_x:
                if r == rows - 1:
                    ax.set_xlabel(ov.get("xlabel", config.xlabel))
                else:
                    ax.set_xlabel("")
                    ax.tick_params(labelbottom=False)
            else:
                ax.set_xlabel(ov.get("xlabel", config.xlabel))

            ax.set_ylabel(ov.get("ylabel", config.ylabel))

            xlim = ov.get("xlim", config.xlimits) or config.xlimits
            ylim = ov.get("ylim", config.ylimits) or config.ylimits
            xticks = ov.get("xticksN", config.xticksN) or config.xticksN
            yticks = ov.get("yticksN", config.yticksN) or config.yticksN

            if xlim is not None:
                ax.set_xlim(xlim)
            if ylim is not None:
                ax.set_ylim(ylim)
            if xticks is not None:
                ax.xaxis.set_major_locator(MaxNLocator(xticks))
            if yticks is not None:
                ax.yaxis.set_major_locator(MaxNLocator(yticks))

            self._apply_minor_ticks(ax, config.minor_ticks)
            ax.grid(config.grid, which="major")
            if config.minor_grid:
                ax.grid(True, which="minor", linestyle=":", linewidth=0.5)
            else:
                ax.grid(False, which="minor")

            artist = subplot_artists.get(i)
            if artist is not None:
                colorbar = self.fig.colorbar(artist, ax=ax)
                colorbar.set_label(subplot_labels.get(i, "Value"))
                self._colorbars.append(colorbar)

    def _draw_3d(self, curves, config):
        max_index = max(0, len(self.axes) - 1)
        subplot_zlabels = {}
        subplot_handles = {}

        for curve in curves:
            i = self._normalized_subplot_index(curve, max_index)
            ax = self.axes[i]
            x, y, z = curve.xyz()
            if z is None:
                continue
            style = self._curve_render_style(curve)
            subplot_zlabels.setdefault(i, curve.z_col or "Z")

            if style == "surface":
                artist, colorbar_label = self._plot_surface_3d(ax, x, y, z, curve)
                if artist is not None:
                    artist.set_label("_nolegend_")
                    self._add_colorbar(ax, artist, colorbar_label or curve.z_col or curve.label)
                    curve._mpl_line = artist
                    subplot_handles.setdefault(i, []).append(
                        (Patch(facecolor=self._representative_rgba(curve), edgecolor="none"), curve.label)
                    )
                continue

            if style == "volume":
                mappable, colorbar_label = self._plot_volume_3d(ax, x, y, z, curve)
                if mappable is not None:
                    self._add_colorbar(ax, mappable, colorbar_label or "Point density")
                    subplot_handles.setdefault(i, []).append(
                        (Patch(facecolor=self._representative_rgba(curve), edgecolor="none", alpha=0.45), curve.label)
                    )
                curve._mpl_line = mappable
                continue

            (line,) = ax.plot(
                x,
                y,
                z,
                label=curve.label,
                color=curve.color,
                marker=curve.marker,
                markersize=curve.marker_size,
                markerfacecolor=curve.marker_face_color,
                markeredgecolor=curve.marker_edge_color,
                linestyle=curve.linestyle,
                linewidth=curve.linewidth,
            )
            curve._mpl_line = line
            subplot_handles.setdefault(i, []).append((line, curve.label))

        for i, ax in enumerate(self.axes):
            ov = config.subplots_config.get(i, {})
            xticks = ov.get("xticksN", config.xticksN) or config.xticksN
            yticks = ov.get("yticksN", config.yticksN) or config.yticksN
            zticks = ov.get("zticksN", getattr(config, "zticksN", None)) or getattr(config, "zticksN", None)

            ax.set_xlabel(ov.get("xlabel", config.xlabel))
            ax.set_ylabel(ov.get("ylabel", config.ylabel))
            ax.set_zlabel(subplot_zlabels.get(i, "Z"))

            xlim = ov.get("xlim", config.xlimits) or config.xlimits
            ylim = ov.get("ylim", config.ylimits) or config.ylimits
            if xlim is not None:
                ax.set_xlim(xlim)
            if ylim is not None:
                ax.set_ylim(ylim)
            if xticks is not None:
                ax.xaxis.set_major_locator(MaxNLocator(xticks))
            if yticks is not None:
                ax.yaxis.set_major_locator(MaxNLocator(yticks))
            if zticks is not None:
                ax.zaxis.set_major_locator(MaxNLocator(zticks))

            ax.grid(config.grid)
            if config.legend and subplot_handles.get(i):
                handles, labels = zip(*subplot_handles[i])
                legend = ax.legend(handles, labels)
                if legend is not None:
                    legend.set_draggable(True)

    def _apply_minor_ticks(self, axis, enabled, include_x=True):
        if enabled:
            axis.minorticks_on()
            if include_x:
                axis.xaxis.set_minor_locator(AutoMinorLocator())
            axis.yaxis.set_minor_locator(AutoMinorLocator())
            return
        axis.minorticks_off()

    def _curve_render_style(self, curve):
        return getattr(curve, "render_style", "line") or "line"

    def _plot_surface_3d(self, ax, x, y, z, curve):
        cmap = self._colormap_for_curve(curve)
        grid = self._grid_from_xyz(x, y, z)
        try:
            if grid is not None:
                xg, yg, zg = grid
                artist = ax.plot_surface(
                    xg,
                    yg,
                    zg,
                    cmap=cmap,
                    linewidth=0,
                    antialiased=True,
                    shade=True,
                    alpha=0.95,
                )
            else:
                artist = ax.plot_trisurf(
                    x,
                    y,
                    z,
                    cmap=cmap,
                    linewidth=0.2,
                    antialiased=True,
                    shade=True,
                )
            return artist, curve.z_col or curve.label
        except Exception:
            line = ax.scatter(x, y, z, c=z, cmap=cmap, s=15, alpha=0.7)
            return line, curve.z_col or curve.label

    def _plot_volume_3d(self, ax, x, y, z, curve):
        if len(x) < 2:
            return None, None

        points = np.column_stack([x, y, z])
        finite = np.isfinite(points).all(axis=1)
        points = points[finite]
        if len(points) < 2:
            return None, None

        bins = max(4, min(18, int(round(len(points) ** (1 / 3))) + 1))
        counts, edges = np.histogramdd(points, bins=bins)
        filled = counts > 0
        if not filled.any():
            return None, None

        x_edges, y_edges, z_edges = edges
        xg, yg, zg = np.meshgrid(x_edges, y_edges, z_edges, indexing="ij")
        cmap = self._colormap_for_curve(curve)
        values = counts[filled]
        if values.size:
            vmin, vmax = float(values.min()), float(values.max())
            if vmin == vmax:
                vmax = vmin + 1.0
            mapper = Normalize(vmin=vmin, vmax=vmax)
            facecolors = cmap(mapper(counts))
            facecolors[~filled, -1] = 0.0
            mappable = ScalarMappable(norm=mapper, cmap=cmap)
            mappable.set_array(counts)
        else:
            facecolors = cmap(np.zeros_like(counts, dtype=float))
            mappable = ScalarMappable(cmap=cmap)
            mappable.set_array(counts)

        try:
            ax.voxels(xg, yg, zg, filled, facecolors=facecolors, edgecolors="none", shade=True)
        except Exception:
            scatter = ax.scatter(
                points[:, 0],
                points[:, 1],
                points[:, 2],
                c=points[:, 2],
                cmap=cmap,
                s=12,
                alpha=0.2,
            )
            return scatter, curve.z_col or "Z"

        ax.set_xlim(float(x_edges[0]), float(x_edges[-1]))
        ax.set_ylim(float(y_edges[0]), float(y_edges[-1]))
        ax.set_zlim(float(z_edges[0]), float(z_edges[-1]))
        return mappable, "Point density"

    def _grid_from_xyz(self, x, y, z):
        try:
            x = np.asarray(x)
            y = np.asarray(y)
            z = np.asarray(z)
        except Exception:
            return None

        finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
        x = x[finite]
        y = y[finite]
        z = z[finite]
        if len(x) < 4:
            return None

        x_vals = np.unique(x)
        y_vals = np.unique(y)
        if len(x_vals) * len(y_vals) != len(x):
            return None

        grid = np.full((len(y_vals), len(x_vals)), np.nan, dtype=float)
        x_index = {value: idx for idx, value in enumerate(x_vals)}
        y_index = {value: idx for idx, value in enumerate(y_vals)}
        for xv, yv, zv in zip(x, y, z):
            grid[y_index[yv], x_index[xv]] = zv

        if np.isnan(grid).any():
            return None

        xg, yg = np.meshgrid(x_vals, y_vals)
        return xg, yg, grid

    def _add_colorbar(self, ax, artist, label):
        try:
            colorbar = self.fig.colorbar(artist, ax=ax)
            colorbar.set_label(label)
            self._colorbars.append(colorbar)
        except Exception:
            pass

    def _representative_rgba(self, curve):
        return self._colormap_for_curve(curve)(0.65)

    def _normalized_subplot_index(self, curve, max_index):
        i = max(0, min(int(curve.subplot_index), max_index))
        if curve.subplot_index != i:
            curve.subplot_index = i
        return i

    def _colormap_for_curve(self, curve):
        colors = PLOTLY_PALETTES.get(curve.palette_name, PLOTLY_PALETTES["Matplotlib default"])
        return LinearSegmentedColormap.from_list(
            f"plotter_{curve.palette_name}_{id(curve)}",
            colors,
        )

    def _remove_colorbars(self):
        for colorbar in self._colorbars:
            try:
                colorbar.remove()
            except Exception:
                pass
        self._colorbars.clear()

    def _create_subplots(self, layout, shared_x=False, shared_y=False, config=None):
        rows, cols = layout
        plot_mode = getattr(config, "plot_mode", "line2d") if config is not None else "line2d"

        self.fig.clear()
        self.axes = []
        self.ax2.clear()
        self._colorbars.clear()

        if plot_mode == "plot3d":
            for index in range(rows * cols):
                self.axes.append(self.fig.add_subplot(rows, cols, index + 1, projection="3d"))
            return

        sharex = "col" if shared_x else False
        sharey = "row" if shared_y else False
        axs = self.fig.subplots(rows, cols, sharex=sharex, sharey=sharey)

        if shared_x and plot_mode == "line2d":
            self.fig.subplots_adjust(hspace=0)
        # 
        # flatten → axs[0], axs[1], ...
        self.axes = list(axs.flat) if hasattr(axs, "flat") else [axs]

    def refresh_legends(self, config):
        """Rebuild legends from the *current* artists without replotting curves."""
        for i, ax in enumerate(self.axes):
            # Remove existing legend if any
            old = ax.get_legend()
            if old is not None:
                old.remove()

            if not config.legend:
                continue

            h, l = ax.get_legend_handles_labels()

            ax2 = self.ax2.get(i)
            if ax2 is not None:
                h2, l2 = ax2.get_legend_handles_labels()
                h += h2
                l += l2

            if h:
                leg = ax.legend(h, l)
                leg.set_draggable(True)

