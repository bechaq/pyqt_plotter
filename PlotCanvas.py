from Color_modules import PLOTLY_PALETTES
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import MaxNLocator, AutoMinorLocator

class PlotCanvas(FigureCanvas):
    def __init__(self):
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        self.ax2 = None
        super().__init__(self.fig)
        
    def clear(self):
        # Clear primary axis
        self.ax.clear()

        # IMPORTANT: remove the twin axis from the figure (not just clear it)
        if self.ax2 is not None:
            self.ax2.remove()
            self.ax2 = None

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
        self.clear()

        palette = PLOTLY_PALETTES.get(config.palette_name, [])
        auto_color_index = 0

        # Plot
        for curve in curves:
            x, y = curve.xy()
            ax = self._get_axis(curve.axis)
            ax.plot(x, y, label=curve.label, color=curve.color, marker=curve.marker, markersize=curve.marker_size, linestyle=curve.linestyle, linewidth=curve.linewidth)
       
        # Axes limits
        if config.xlimits is not None:
            self.ax.set_xlim(config.xlimits)
        if config.ylimits is not None:
            self.ax.set_ylim(config.ylimits)
        if self.ax2 is not None and config.ylimits is not None:
            self.ax2.set_ylim(config.ylimits)

        # Labels (primary always)
        self.ax.set_xlabel(config.xlabel)
        self.ax.set_ylabel(config.ylabel)

        # Ticks
        if config.xticksN is not None:
            self.ax.xaxis.set_major_locator(MaxNLocator(nbins=config.xticksN))
        if config.yticksN is not None:
            self.ax.yaxis.set_major_locator(MaxNLocator(nbins=config.yticksN))

        # Minor ticks
        if config.minor_ticks:
            self.ax.xaxis.set_minor_locator(AutoMinorLocator())
            self.ax.yaxis.set_minor_locator(AutoMinorLocator())

            if self.ax2 is not None:
                self.ax2.yaxis.set_minor_locator(AutoMinorLocator())


        # Size
        w, h = self.ratio_to_inches(config.ratio)
        self.fig.set_size_inches(w,h)
        if config.dirty:
            self.fig.tight_layout()
            config.dirty = False


        # Grid (usually only on primary looks best)
        if config.grid:
            self.ax.grid(True)
        if config.minor_grid:
            self.ax.grid(which="minor", linestyle=":", linewidth=0.5)
        else:
            self.ax.grid(which="minor", visible=False)
        if self.ax2 is not None:
            if config.grid:
                self.ax2.grid(True)
            if config.minor_grid:
                self.ax2.grid(which="minor", linestyle=":", linewidth=0.5)
            else:
                self.ax2.grid(which="minor", visible=False)


        # Legend: combine handles from both axes into ONE legend
        if config.legend:
            handles, labels = self.ax.get_legend_handles_labels()
            if self.ax2 is not None:
                h2, l2 = self.ax2.get_legend_handles_labels()
                handles += h2
                labels += l2
            if handles:
                self.ax.legend(handles, labels)

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

