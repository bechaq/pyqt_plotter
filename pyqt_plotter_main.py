import os
import sys
from MainWindow import MainWindow
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication


def _app_icon():
     root = os.path.dirname(__file__)
     candidates = [
          "Logo.icns",
          "Logo.png",
          "Logo.ico",
     ]
     for name in candidates:
          path = os.path.join(root, name)
          if os.path.exists(path):
               return QIcon(path)
     return QIcon()


def dynamic_plotter_app():
     if hasattr(Qt, "AA_EnableHighDpiScaling"):
          QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
     if hasattr(Qt, "AA_UseHighDpiPixmaps"):
          QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

     app = QApplication(sys.argv)
     app.setApplicationName("Clean PyQt Plotter")
     app.setOrganizationName("Clean PyQt Plotter")
     icon = _app_icon()
     if not icon.isNull():
          app.setWindowIcon(icon)
     win = MainWindow(prompt_for_mode=True)
     if getattr(win, "_startup_cancelled", False):
          win.close()
          return 0
     if not icon.isNull():
          win.setWindowIcon(icon)
     win.show()
     return app.exec_()

if __name__ == "__main__":
    sys.exit(dynamic_plotter_app())
