class PlotConfig:
    def __init__(self):
        self.xlabel = "X"
        self.ylabel = "Y"
        self.grid = True              # major grid
        self.minor_grid = False       # minor grid
        self.minor_ticks = False      

        self.legend = True
        self.palette_name = "Plotly"
        self.ratio = (1,1)
        self.dirty = False
        self.xlimits = None  # (min, max) or None
        self.ylimits = None  # (min, max) or None
        self.xticksN = None  # number of ticks or None
        self.yticksN = None  # number of ticks or None
        self.subplots = False  # number of subplots
        self.suplot_layout = (1, 1)  # (rows, cols) if subplots is True
