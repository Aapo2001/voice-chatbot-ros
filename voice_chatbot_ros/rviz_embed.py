"""
RViz2 embed panel – launches rviz2 as a subprocess and attempts to
embed its window into the PySide6 application.

Falls back to a "running in separate window" label if embedding fails.
"""

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QProcess, Qt, QTimer
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

log = logging.getLogger(__name__)

# Path to the default RViz config shipped with inmoov_description.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_RVIZ_CONFIG = _PROJECT_ROOT / "src" / "inmoov_description" / "config" / "inmoov.rviz"


def _find_rviz_window_win32() -> int | None:
    """Find the RViz2 window handle on Windows using EnumWindows."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    EnumWindows = user32.EnumWindows
    GetWindowTextW = user32.GetWindowTextW
    GetWindowTextLengthW = user32.GetWindowTextLengthW
    IsWindowVisible = user32.IsWindowVisible

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    result = []

    def callback(hwnd, _lparam):
        if IsWindowVisible(hwnd):
            length = GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.lower()
                if "rviz" in title:
                    result.append(hwnd)
                    return False  # stop enumeration
        return True

    EnumWindows(WNDENUMPROC(callback), 0)
    return result[0] if result else None


def _find_rviz_window_x11() -> int | None:
    """Find the RViz2 X11 window ID using xdotool."""
    import subprocess

    try:
        out = subprocess.run(
            ["xdotool", "search", "--name", "rviz"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return int(out.stdout.strip().splitlines()[0])
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
        pass
    return None


class RVizEmbedPanel(QWidget):
    """Launches rviz2 and attempts to embed its window."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._process: QProcess | None = None
        self._container: QWidget | None = None
        self._embed_attempts = 0

        self._build_ui()

    def _build_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)

        title = QLabel("RViz")
        title.setStyleSheet("font-weight: bold; font-size: 13px; padding: 2px;")
        self._layout.addWidget(title)

        self._placeholder = QLabel("RViz ei käynnissä")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._placeholder.setStyleSheet(
            "QLabel { background-color: #11111b; color: #6c7086; "
            "border: 1px solid #45475a; border-radius: 4px; }"
        )
        self._layout.addWidget(self._placeholder)

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning

    def start_rviz(self, config_path: str | None = None) -> None:
        """Launch rviz2 and attempt to embed after a delay."""
        if self.is_running:
            return

        rviz_cfg = config_path or str(_DEFAULT_RVIZ_CONFIG)
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._process.finished.connect(self._on_process_finished)

        self._process.start("rviz2", ["-d", rviz_cfg])
        self._placeholder.setText("RViz käynnistyy...")
        self._embed_attempts = 0
        QTimer.singleShot(3000, self._attempt_embed)

    def stop_rviz(self) -> None:
        """Terminate rviz2."""
        if self._container is not None:
            self._layout.removeWidget(self._container)
            self._container.setParent(None)
            self._container.deleteLater()
            self._container = None

        if self._process is not None:
            self._process.terminate()
            self._process.waitForFinished(3000)
            if self._process.state() != QProcess.ProcessState.NotRunning:
                self._process.kill()
            self._process = None

        self._placeholder.setText("RViz ei käynnissä")
        self._placeholder.show()

    def _attempt_embed(self) -> None:
        """Try to find and embed the rviz2 window."""
        if not self.is_running:
            return

        self._embed_attempts += 1

        if sys.platform == "win32":
            wid = _find_rviz_window_win32()
        else:
            wid = _find_rviz_window_x11()

        if wid is not None:
            try:
                window = QWindow.fromWinId(wid)
                container = QWidget.createWindowContainer(window, self)
                container.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
                self._placeholder.hide()
                self._layout.addWidget(container)
                self._container = container
                log.info("RViz window embedded (wid=%s)", wid)
                return
            except Exception as exc:
                log.warning("Failed to embed RViz window: %s", exc)

        if self._embed_attempts < 5:
            QTimer.singleShot(2000, self._attempt_embed)
        else:
            self._placeholder.setText(
                "RViz käynnissä erillisessä ikkunassa"
            )
            log.info("RViz embedding failed after %d attempts, running standalone", self._embed_attempts)

    def _on_process_finished(self, exit_code: int, _status) -> None:
        if self._container is not None:
            self._layout.removeWidget(self._container)
            self._container.setParent(None)
            self._container.deleteLater()
            self._container = None
        self._process = None
        self._placeholder.setText("RViz ei käynnissä")
        self._placeholder.show()
