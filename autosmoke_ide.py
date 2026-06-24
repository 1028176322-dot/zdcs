"""AutoSmoke IDE launcher.

This file was restored to a clean, path-independent version so it can run on
other machines.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

from AutoSmoke.config_manager import get_game_resolution, set_game_resolution


def get_project_root() -> Path:
    return Path(__file__).resolve().parent


def get_autosmoke_dir() -> Path:
    root = get_project_root()
    autosmoke_dir = root / "AutoSmoke"
    if autosmoke_dir.exists():
        return autosmoke_dir
    for parent in root.parents:
        candidate = parent / "AutoSmoke"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("AutoSmoke directory not found")


PROJECT_ROOT = get_project_root()
AUTOSMOKE_DIR = get_autosmoke_dir()


def resolve_script_path(base_dir: Path, script_name: str) -> Optional[Path]:
    direct = base_dir / script_name
    if direct.exists():
        return direct

    matches = list(base_dir.glob(f"**/{script_name}"))
    return matches[0] if matches else None


try:
    from PyQt6.QtCore import QThread, pyqtSignal
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QApplication,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    PYQT_AVAILABLE = True
except ImportError as err:  # pragma: no cover
    PYQT_AVAILABLE = False
    _IMPORT_ERROR = err


class WorkerThread(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, script_path: str, autosmoke_dir: Path) -> None:
        super().__init__()
        self.script_path = script_path
        self.autosmoke_dir = autosmoke_dir

    def run(self) -> None:
        try:
            self.output_signal.emit(f"Start: {self.script_path}")
            process = subprocess.Popen(
                [sys.executable, self.script_path],
                cwd=str(self.autosmoke_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            if process.stdout is not None:
                for line in process.stdout:
                    self.output_signal.emit(line.rstrip("\n"))

            return_code = process.wait()
            if return_code == 0:
                self.finished_signal.emit(True, "Script finished successfully")
            else:
                self.finished_signal.emit(False, f"Script exited with code: {return_code}")
        except Exception as exc:  # pragma: no cover
            self.finished_signal.emit(False, f"Run failed: {exc}")


class AutoSmokeIDE(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.project_root = PROJECT_ROOT
        self.autosmoke_dir = AUTOSMOKE_DIR
        self.worker: Optional[WorkerThread] = None
        self.init_ui()
        self.load_settings()

    def init_ui(self) -> None:
        self.setWindowTitle("AutoSmoke IDE - Unity")
        self.setGeometry(100, 100, 1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        config_group = QGroupBox("Game resolution")
        config_layout = QFormLayout(config_group)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 10000)
        self.width_spin.setValue(1170)
        self.width_spin.setSuffix(" px")

        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 10000)
        self.height_spin.setValue(2532)
        self.height_spin.setSuffix(" px")

        self.save_config_btn = QPushButton("Save settings")
        self.save_config_btn.clicked.connect(self.save_settings)

        config_layout.addRow("Width", self.width_spin)
        config_layout.addRow("Height", self.height_spin)
        config_layout.addRow("", self.save_config_btn)
        layout.addWidget(config_group)

        script_group = QGroupBox("Scripts")
        script_layout = QVBoxLayout(script_group)

        row1 = QHBoxLayout()
        self.btn_visualize = QPushButton("Visualize clickable elements")
        self.btn_visualize.clicked.connect(lambda: self.run_script("visualize_clickable_elements.py"))
        row1.addWidget(self.btn_visualize)

        self.btn_locate = QPushButton("Locate game region")
        self.btn_locate.clicked.connect(lambda: self.run_script("locate_active_region.py"))
        row1.addWidget(self.btn_locate)
        script_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.btn_auto_click = QPushButton("Auto click test")
        self.btn_auto_click.setEnabled(False)
        self.btn_generate = QPushButton("Generate test cases")
        self.btn_generate.setEnabled(False)
        row2.addWidget(self.btn_auto_click)
        row2.addWidget(self.btn_generate)
        script_layout.addLayout(row2)

        layout.addWidget(script_group)

        output_group = QGroupBox("Run output")
        output_layout = QVBoxLayout(output_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setMinimumHeight(300)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.output_text.clear)

        output_layout.addWidget(self.output_text)
        output_layout.addWidget(clear_btn)
        layout.addWidget(output_group)

        self.statusBar().showMessage("Ready")

        self.set_buttons_enabled(True)

    def load_settings(self) -> None:
        try:
            width, height = get_game_resolution()
            self.width_spin.setValue(width)
            self.height_spin.setValue(height)
            self.log(f"Loaded config: {width}x{height}")
        except Exception as exc:
            self.log(f"Failed to load config: {exc}")

    def save_settings(self) -> None:
        try:
            set_game_resolution(self.width_spin.value(), self.height_spin.value())
            QMessageBox.information(self, "Configuration", "Settings saved")
            self.log(f"Saved resolution: {self.width_spin.value()}x{self.height_spin.value()}")
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "Error", f"Failed to save: {exc}")
            self.log(f"Save failed: {exc}")

    def run_script(self, script_name: str) -> None:
        script_path = resolve_script_path(self.autosmoke_dir, script_name)
        if script_path is None:
            QMessageBox.warning(self, "Script not found", f"Could not find script: {script_name}")
            self.log(f"Missing script: {script_name}")
            return

        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Busy", "A script is already running")
            return

        self.set_buttons_enabled(False)
        self.worker = WorkerThread(str(script_path), self.autosmoke_dir)
        self.worker.output_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_script_finished)
        self.worker.start()
        self.statusBar().showMessage(f"Running {script_name}...")

    def on_script_finished(self, success: bool, message: str) -> None:
        self.set_buttons_enabled(True)
        self.log(message)
        self.statusBar().showMessage(message)
        if success:
            QMessageBox.information(self, "Done", message)
        else:
            QMessageBox.warning(self, "Failed", message)

    def set_buttons_enabled(self, enabled: bool) -> None:
        self.btn_visualize.setEnabled(enabled)
        self.btn_locate.setEnabled(enabled)
        self.btn_auto_click.setEnabled(enabled)
        self.btn_generate.setEnabled(enabled)
        self.save_config_btn.setEnabled(enabled)

    def log(self, message: str) -> None:
        self.output_text.append(str(message))
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


def main() -> None:
    if not PYQT_AVAILABLE:
        print("AutoSmoke IDE requires PyQt6 to run.")
        print(f"Import failed: {_IMPORT_ERROR}")
        print("Run: python -m pip install PyQt6")
        return

    app = QApplication(sys.argv)
    window = AutoSmokeIDE()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
