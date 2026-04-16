"""
Unified SOP-Robot GUI – combines RViz, camera image viewer, and
voice chatbot into a single PySide6 window.

Usage::

    pixi run ros-unified-ui
"""

import sys

from voice_chatbot.platform_setup import setup_pyside6

setup_pyside6()

import rclpy
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from voice_chatbot.config import Config
from voice_chatbot.ui_common import (
    APP_STYLESHEET,
    SettingsPanel,
    append_chat,
    append_log,
    update_status_label,
)

from voice_chatbot_ros.image_viewer import ImageViewerPanel
from voice_chatbot_ros.ros_app import RosBridge
from voice_chatbot_ros.rviz_embed import RVizEmbedPanel

# ── Button styles (shared with ros_app.py) ───────────────────────

_BTN_GREEN = (
    "QPushButton { background-color: #2e7d32; color: white; "
    "font-weight: bold; padding: 4px 16px; border-radius: 4px; }"
    "QPushButton:hover { background-color: #388e3c; }"
    "QPushButton:disabled { background-color: #666; }"
)
_BTN_RED = (
    "QPushButton { background-color: #c62828; color: white; "
    "font-weight: bold; padding: 4px 16px; border-radius: 4px; }"
    "QPushButton:hover { background-color: #d32f2f; }"
    "QPushButton:disabled { background-color: #666; }"
)
_BTN_BLUE = (
    "QPushButton { background-color: #1565c0; color: white; "
    "font-weight: bold; padding: 4px 16px; border-radius: 4px; }"
    "QPushButton:hover { background-color: #1976d2; }"
)
_BTN_ORANGE = (
    "QPushButton { background-color: #e65100; color: white; "
    "font-weight: bold; padding: 4px 16px; border-radius: 4px; }"
    "QPushButton:hover { background-color: #ef6c00; }"
    "QPushButton:disabled { background-color: #666; }"
)


class UnifiedWindow(QMainWindow):
    """Single window combining RViz, image viewer, and voice chatbot."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SOP-Robot – Unified UI")
        self.resize(1400, 850)

        self._config = Config.load()
        self._bridge = RosBridge(self)
        self._settings_visible = False

        self._build_ui()
        self._connect_signals()
        self._set_connected_state(False)

    def _build_ui(self) -> None:
        # ── Toolbar ──
        toolbar = self.addToolBar("Hallinta")
        toolbar.setMovable(False)

        self.btn_connect = QPushButton("  Yhdistä")
        self.btn_connect.setMinimumHeight(32)
        self.btn_connect.setStyleSheet(_BTN_GREEN)
        toolbar.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("  Katkaise")
        self.btn_disconnect.setMinimumHeight(32)
        self.btn_disconnect.setStyleSheet(_BTN_RED)
        toolbar.addWidget(self.btn_disconnect)

        toolbar.addSeparator()

        self.btn_start_rviz = QPushButton("  Käynnistä RViz")
        self.btn_start_rviz.setMinimumHeight(32)
        self.btn_start_rviz.setStyleSheet(_BTN_ORANGE)
        toolbar.addWidget(self.btn_start_rviz)

        self.btn_stop_rviz = QPushButton("  Pysäytä RViz")
        self.btn_stop_rviz.setMinimumHeight(32)
        self.btn_stop_rviz.setEnabled(False)
        toolbar.addWidget(self.btn_stop_rviz)

        toolbar.addSeparator()

        self.btn_toggle_settings = QPushButton("  Asetukset")
        self.btn_toggle_settings.setMinimumHeight(32)
        self.btn_toggle_settings.setCheckable(True)
        toolbar.addWidget(self.btn_toggle_settings)

        self.btn_save = QPushButton("  Tallenna")
        self.btn_save.setMinimumHeight(32)
        self.btn_save.setStyleSheet(_BTN_BLUE)
        self.btn_save.setToolTip("Tallenna asetukset config.json-tiedostoon")
        toolbar.addWidget(self.btn_save)

        self.btn_clear = QPushButton("  Tyhjennä")
        self.btn_clear.setMinimumHeight(32)
        toolbar.addWidget(self.btn_clear)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        self.label_status = QLabel("Tila: Ei yhdistetty")
        self.label_status.setTextFormat(Qt.TextFormat.RichText)
        self.label_status.setStyleSheet("font-weight: bold; padding-right: 12px;")
        toolbar.addWidget(self.label_status)

        # ── Central area ──
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Settings panel (hidden by default)
        self.settings_panel = SettingsPanel(self._config)
        self.settings_panel.setVisible(False)
        main_layout.addWidget(self.settings_panel)

        # Main splitter: left (viz) | right (chat)
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter.setChildrenCollapsible(False)

        # ── Left column: RViz + Image viewer ──
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_splitter.setChildrenCollapsible(False)

        self.rviz_panel = RVizEmbedPanel()
        left_splitter.addWidget(self.rviz_panel)

        self.image_viewer = ImageViewerPanel()
        left_splitter.addWidget(self.image_viewer)

        left_splitter.setSizes([400, 300])
        self._main_splitter.addWidget(left_splitter)

        # ── Right column: Chat + Input + Log ──
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setChildrenCollapsible(False)

        # Chat panel
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_label = QLabel("Keskustelu")
        chat_label.setStyleSheet("font-weight: bold; font-size: 13px; padding: 2px;")
        chat_layout.addWidget(chat_label)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 11))
        self.chat_display.setStyleSheet(
            "QTextEdit { background-color: #1e1e2e; color: #cdd6f4; "
            "border: 1px solid #45475a; border-radius: 4px; padding: 8px; }"
        )
        chat_layout.addWidget(self.chat_display)

        # Text input row
        input_row = QHBoxLayout()
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Kirjoita viesti...")
        self.text_input.setMinimumHeight(32)
        self.text_input.setFont(QFont("Segoe UI", 11))
        self.btn_send = QPushButton("Lähetä")
        self.btn_send.setMinimumHeight(32)
        self.btn_send.setStyleSheet(_BTN_GREEN)
        input_row.addWidget(self.text_input)
        input_row.addWidget(self.btn_send)
        chat_layout.addLayout(input_row)
        right_splitter.addWidget(chat_container)

        # Log panel
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_label = QLabel("Järjestelmäloki")
        log_label.setStyleSheet("font-weight: bold; font-size: 13px; padding: 2px;")
        log_layout.addWidget(log_label)

        self.log_display = QPlainTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Cascadia Mono, Consolas, Courier New", 9))
        self.log_display.setMaximumBlockCount(2000)
        self.log_display.setStyleSheet(
            "QPlainTextEdit { background-color: #11111b; color: #a6adc8; "
            "border: 1px solid #45475a; border-radius: 4px; padding: 4px; }"
        )
        log_layout.addWidget(self.log_display)
        right_splitter.addWidget(log_container)

        right_splitter.setSizes([480, 200])
        right_layout.addWidget(right_splitter)
        self._main_splitter.addWidget(right_widget)

        self._main_splitter.setSizes([550, 550])
        main_layout.addWidget(self._main_splitter, stretch=1)

        self.statusBar().showMessage("Ei yhdistetty")

    def _connect_signals(self) -> None:
        self.btn_connect.clicked.connect(self._on_connect)
        self.btn_disconnect.clicked.connect(self._on_disconnect)
        self.btn_start_rviz.clicked.connect(self._on_start_rviz)
        self.btn_stop_rviz.clicked.connect(self._on_stop_rviz)
        self.btn_toggle_settings.toggled.connect(self._on_toggle_settings)
        self.btn_save.clicked.connect(self._on_save_settings)
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_send.clicked.connect(self._on_send)
        self.text_input.returnPressed.connect(self._on_send)

        Q = Qt.ConnectionType.QueuedConnection
        self._bridge.log_received.connect(lambda t: append_log(self.log_display, t), Q)
        self._bridge.status_received.connect(
            lambda t: update_status_label(self.label_status, self.statusBar(), t), Q
        )
        self._bridge.chat_message.connect(
            lambda r, t: append_chat(self.chat_display, r, t), Q
        )

    def _set_connected_state(self, connected: bool) -> None:
        self.btn_connect.setEnabled(not connected)
        self.btn_disconnect.setEnabled(connected)
        self.btn_send.setEnabled(connected)
        self.text_input.setEnabled(connected)

    # ── Slots ──

    def _on_connect(self) -> None:
        try:
            self._bridge.connect_ros()
            self._set_connected_state(True)
            self.image_viewer.set_node(self._bridge._node)
            update_status_label(self.label_status, self.statusBar(), "Yhdistetty")
            append_log(self.log_display, "ROS 2 -yhteys muodostettu.")
        except Exception as exc:
            append_log(self.log_display, f"VIRHE: ROS 2 -yhteys epäonnistui: {exc}")

    def _on_disconnect(self) -> None:
        self.image_viewer.detach_node()
        self._bridge.disconnect_ros()
        self._set_connected_state(False)
        update_status_label(self.label_status, self.statusBar(), "Ei yhdistetty")
        append_log(self.log_display, "ROS 2 -yhteys katkaistu.")

    def _on_start_rviz(self) -> None:
        self.rviz_panel.start_rviz()
        self.btn_start_rviz.setEnabled(False)
        self.btn_stop_rviz.setEnabled(True)
        append_log(self.log_display, "RViz käynnistetty.")

    def _on_stop_rviz(self) -> None:
        self.rviz_panel.stop_rviz()
        self.btn_start_rviz.setEnabled(True)
        self.btn_stop_rviz.setEnabled(False)
        append_log(self.log_display, "RViz pysäytetty.")

    def _on_toggle_settings(self, checked: bool) -> None:
        self.settings_panel.setVisible(checked)
        self._settings_visible = checked

    def _on_save_settings(self) -> None:
        cfg = Config()
        self.settings_panel.write_to_config(cfg)
        cfg.save()
        append_log(self.log_display, "Asetukset tallennettu config.json-tiedostoon.")

    def _on_clear(self) -> None:
        self.chat_display.clear()
        self._bridge.clear_history()

    def _on_send(self) -> None:
        text = self.text_input.text().strip()
        if not text:
            return
        self.text_input.clear()
        self._bridge.send_text(text)

    def closeEvent(self, event) -> None:
        self.image_viewer.detach_node()
        self.rviz_panel.stop_rviz()
        self._bridge.disconnect_ros()
        event.accept()


# ── Entry point ───────────────────────────────────────────────────


def _suppress_qpainter_warnings():
    from PySide6.QtCore import QtMsgType, qInstallMessageHandler

    def handler(msg_type, context, message):
        if msg_type == QtMsgType.QtWarningMsg and "QPainter" in message:
            return
        sys.stderr.write(f"{message}\n")

    qInstallMessageHandler(handler)


def main() -> None:
    app = QApplication(sys.argv)
    _suppress_qpainter_warnings()
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    window = UnifiedWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
