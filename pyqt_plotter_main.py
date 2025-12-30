import sys
from MainWindow import *
from PyQt5.QtWidgets import QApplication
def dynamic_plotter_app():
     app = QApplication(sys.argv)
     win = MainWindow()
     win.show()
     sys.exit(app.exec_())

if __name__ == "__main__":
    dynamic_plotter_app()
