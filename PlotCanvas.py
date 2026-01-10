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
        self._last_shared_x = None
        self._last_shared_y = None
     #### Premiere fois, creer subplot par defaut et ov par defaut, ensuite xtickN change pas
        super().__init__(self.fig)
        
    def clear(self, layout, config):
        need_rebuild = (
        self._last_layout != layout
        or self._last_shared_x != config.shared_x
        or self._last_shared_y != config.shared_y

    )

        if need_rebuild:
            self._create_subplots(layout, config.shared_x, config.shared_y, config)
            self._last_layout = layout
            self._last_shared_x = config.shared_x
            self._last_shared_y = config.shared_y
            
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
        print("Drawing")
        # 1) Create/clear axes
        self.clear(config.subplot_layout, config)   # your clear() handles fig.subplots + clearing


        # 2) Plot curves in their subplot
        for curve in curves:
            i = int(curve.subplot_index)
            i = max(0, min(i, len(self.axes) - 1))  # clamp

            ax = self.axes[i]

            if curve.axis == "secondary":
                ax = self.ax2.setdefault(i, ax.twinx())

            x, y = curve.xy()
            (line,) = ax.plot(
                x, y,
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

        # 3) Apply config to *each* subplot (and its secondary axis if present)
        for i, ax in enumerate(self.axes):
            ov = config.subplots_config.get(i, {})
            rows, cols = config.subplot_layout
            r, c = divmod(i, cols)
            # shared_x rule: xlabel/xlim/xticks must be global
            if config.shared_x:
                if r == rows-1:  # bottom row
                    ax.set_xlabel(ov.get("xlabel", config.xlabel))
                else:
                    ax.set_xlabel("")
                    ax.tick_params(labelbottom=False)

                # xlim = ov.get("xlim", config.xlimits) or config.xlimits
                xtN  = ov.get("xticksN", config.xticksN) or config.xticksN
            else:
                ax.set_xlabel(ov.get("xlabel", config.xlabel))

                # xlim = ov.get("xlim", config.xlimits) or config.xlimits
                xtN  = ov.get("xticksN", config.xticksN) or config.xticksN
                
            # y is per subplot (unless you later decide shared_y similar)
            ax.set_ylabel(ov.get("ylabel", config.ylabel))
            # ylim = ov.get("ylim", config.ylimits) or config.ylimits
            ytN  = ov.get("yticksN", config.yticksN) or config.yticksN

            # if xlim is not None: ax.set_xlim(xlim)
            # if ylim is not None: ax.set_ylim(ylim)

            if xtN is not None: ax.xaxis.set_major_locator(MaxNLocator(xtN))
            if ytN is not None: ax.yaxis.set_major_locator(MaxNLocator(ytN))

            # remove last tick label for subplots with shared x to avoid overlap
            if rows > 1 and config.shared_x and r > 0:
                yticks = ax.get_yticklabels()

                if yticks:
                    yticks[-1].set_visible(False)

        # for i, ax in enumerate(self.axes):
            ax2 = self.ax2.get(i)

            # # ---- Limits ----
            # if config.xlimits is not None:
            #     ax.set_xlim(config.xlimits)
            # if config.ylimits is not None:
            #     ax.set_ylim(config.ylimits)
            #     if ax2 is not None:
            #         ax2.set_ylim(config.ylimits)   # optional: separate secondary y-limits later


            # # ---- Major tick count (auto-spaced) ----
            # if config.xticksN is not None:
            #     ax.xaxis.set_major_locator(MaxNLocator(nbins=config.xticksN))
            # if config.yticksN is not None:
            #     ax.yaxis.set_major_locator(MaxNLocator(nbins=config.yticksN))
            #     if ax2 is not None:
            #         ax2.yaxis.set_major_locator(MaxNLocator(nbins=config.yticksN))

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
                    legend = ax.legend(h, l)
                    legend.set_draggable(True)

        # Size
        w, h = self.ratio_to_inches(config.ratio)

        self.fig.set_size_inches(w,h)

        if config.dirty:
            # tighter layout, but don't re-add vertical gaps when sharex
            if config.shared_x and rows> 1:
                # self.fig.tight_layout(h_pad=0.0)
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
    
    def _create_subplots(self, layout, shared_x=False, shared_y=False, config=None):
        rows, cols = layout

        self.fig.clear()
        sharex = "col" if shared_x else False
        sharey = "row" if shared_y else False
        axs = self.fig.subplots(rows, cols, sharex=sharex, sharey=sharey)

        if shared_x:
            self.fig.subplots_adjust(hspace=0)
        # 
        # flatten → axs[0], axs[1], ...
        self.axes = list(axs.flat) if hasattr(axs, "flat") else [axs]
        self.ax2.clear()

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

