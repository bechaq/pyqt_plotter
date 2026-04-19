import json
import os
from pathlib import Path
from PyQt5.QtCore import QStandardPaths


def _storage_dir() -> Path:
    override = os.getenv("PYQT_PLOTTER_APPDATA")
    if override:
        root = Path(override)
    else:
        base = QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation)
        if base:
            root = Path(base) / "PyQtPlotter"
        else:
            root = Path.home() / ".pyqt_plotter"
    root.mkdir(parents=True, exist_ok=True)
    return root


class StateStore:
    def __init__(self):
        self.root = _storage_dir()
        self.autosave_file = self.root / "autosave.json"
        self.recent_file = self.root / "recent_projects.json"

    def save_autosave(self, payload: dict):
        self.autosave_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_autosave(self):
        if not self.autosave_file.exists():
            return None
        return json.loads(self.autosave_file.read_text(encoding="utf-8"))

    def clear_autosave(self):
        if self.autosave_file.exists():
            self.autosave_file.unlink()

    def load_recent_projects(self):
        if not self.recent_file.exists():
            return []
        try:
            data = json.loads(self.recent_file.read_text(encoding="utf-8"))
        except Exception:
            return []
        projects = []
        for path in data:
            if isinstance(path, str) and os.path.exists(path):
                projects.append(path)
        return projects

    def save_recent_projects(self, projects):
        self.recent_file.write_text(json.dumps(projects[:10], indent=2), encoding="utf-8")

    def remember_project(self, path: str):
        path = os.path.abspath(path)
        projects = [p for p in self.load_recent_projects() if os.path.abspath(p) != path]
        projects.insert(0, path)
        self.save_recent_projects(projects)
