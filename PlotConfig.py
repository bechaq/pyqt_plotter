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
        self.xticksN = 6  # number of ticks or None
        self.yticksN = 6  # number of ticks or None
        self.subplots = False  # number of subplots
        self.subplot_layout = (1, 1)  # (rows, cols) if subplots is True
        self.shared_x = False
        self.shared_y = False
        
        self.subplots_config = {}  # idx -> dict with keys: xlabel,ylabel,xlim,ylim,xticksN,yticksN

