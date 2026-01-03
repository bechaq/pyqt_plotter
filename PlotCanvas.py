from Color_modules import PLOTLY_PALETTES
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import MaxNLocator, AutoMinorLocator

class PlotCanvas(FigureCanvas):
    def __init__(self):
        self.fig = Figure()
        self.axes = []
        self.ax2 = {}          # secondary axes per subplot
        self._last_layout = None
        super().__init__(self.fig)
        
    def clear(self, layout):
        if self._last_layout != layout:
            self._create_subplots(layout)
            self._last_layout = layout
        else:
            for ax in self.axes:
                ax.clear()
            for ax2 in self.ax2.values():
                ax2.remove()
            self.ax2.clear()


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
        
        # 1) Create/clear axes
        self.clear(config.subplot_layout)   # your clear() handles fig.subplots + clearing


        # 2) Plot curves in their subplot
        for curve in curves:
            i = int(curve.subplot_index)
            i = max(0, min(i, len(self.axes) - 1))  # clamp

            ax = self.axes[i]

            if curve.axis == "secondary":
                ax = self.ax2.setdefault(i, ax.twinx())

            x, y = curve.xy()
            ax.plot(
                x, y,
                label=curve.label,
                color=curve.color,
                marker=curve.marker,
                markersize=curve.marker_size,
                linestyle=curve.linestyle,
                linewidth=curve.linewidth,
            )

        # 3) Apply config to *each* subplot (and its secondary axis if present)
        for i, ax in enumerate(self.axes):
            ax2 = self.ax2.get(i)

            # ---- Limits ----
            if config.xlimits is not None:
                ax.set_xlim(config.xlimits)
            if config.ylimits is not None:
                ax.set_ylim(config.ylimits)
                if ax2 is not None:
                    ax2.set_ylim(config.ylimits)   # optional: separate secondary y-limits later

            # ---- Labels ----
            # Typical subplot convention: only label outer axes
            rows, cols = config.subplot_layout
            r, c = divmod(i, cols)

            if r == rows - 1:                 # bottom row
                ax.set_xlabel(config.xlabel)
            if c == 0:                        # left column
                ax.set_ylabel(config.ylabel)

            # ---- Major tick count (auto-spaced) ----
            if config.xticksN is not None:
                ax.xaxis.set_major_locator(MaxNLocator(nbins=config.xticksN))
            if config.yticksN is not None:
                ax.yaxis.set_major_locator(MaxNLocator(nbins=config.yticksN))
                if ax2 is not None:
                    ax2.yaxis.set_major_locator(MaxNLocator(nbins=config.yticksN))

            # ---- Minor ticks ----
            if config.minor_ticks:
                ax.minorticks_on()
                ax.xaxis.set_minor_locator(AutoMinorLocator())
                ax.yaxis.set_minor_locator(AutoMinorLocator())
                if ax2 is not None:
                    ax2.minorticks_on()
                    ax2.yaxis.set_minor_locator(AutoMinorLocator())
            else:
                ax.minorticks_off()
                if ax2 is not None:
                    ax2.minorticks_off()

            # ---- Grid ----
            ax.grid(config.grid, which="major")

            if config.minor_grid:
                ax.minorticks_on()
                ax.grid(True, which="minor", linestyle=":", linewidth=0.5)
            else:
                ax.minorticks_off()
                ax.grid(False, which="minor")

            # Secondary grids usually look messy; keep them off by default
            if ax2 is not None:
                ax2.grid(False, which="both")

            # ---- Legend ----
            if config.legend:
                h, l = ax.get_legend_handles_labels()
                if ax2 is not None:
                    h2, l2 = ax2.get_legend_handles_labels()
                    h += h2
                    l += l2
                if h:
                    ax.legend(h, l)

        # Size
        w, h = self.ratio_to_inches(config.ratio)

        self.fig.set_size_inches(w,h)
        if config.dirty:
            self.fig.tight_layout()
            config.dirty = False
        self.draw_idle()


    def _get_axis(self, axis):

        if axis == "primary":
            return self.ax
        elif axis == "secondary":
            if self.ax2 is None:
                self.ax2 = self.ax.twinx()
            return self.ax2
        else:
            raise ValueError("Unknown axis")
    
    def _create_subplots(self, layout):
        rows, cols = layout

        self.fig.clear()
        axs = self.fig.subplots(rows, cols)

        # flatten → axs[0], axs[1], ...
        self.axes = list(axs.flat) if hasattr(axs, "flat") else [axs]
        self.ax2.clear()

