"""
ROS 2 Image Viewer panel – subscribes to sensor_msgs/Image topics
and displays frames in a QLabel, similar to rqt_image_view.
"""

import numpy as np
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from rclpy.node import Node as RosNode
from sensor_msgs.msg import Image as RosImage


class _ImageBridge(QObject):
    """Marshals ROS image callbacks to the Qt main thread."""

    image_ready = Signal(QImage)


class ImageViewerPanel(QWidget):
    """Displays a live ROS camera feed with a topic selector dropdown."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._node: RosNode | None = None
        self._sub = None
        self._bridge = _ImageBridge(self)
        self._bridge.image_ready.connect(self._update_image)
        self._discovery_timer = QTimer(self)
        self._discovery_timer.timeout.connect(self._discover_topics)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel("Kamerakuva")
        title.setStyleSheet("font-weight: bold; font-size: 13px; padding: 2px;")
        header.addWidget(title)

        self.combo_topic = QComboBox()
        self.combo_topic.setMinimumWidth(200)
        self.combo_topic.addItem("(ei aihetta)", "")
        self.combo_topic.currentIndexChanged.connect(self._on_topic_changed)
        header.addWidget(self.combo_topic)
        header.addStretch()
        layout.addLayout(header)

        self.image_label = QLabel("Ei kuvaa")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.image_label.setMinimumSize(320, 240)
        self.image_label.setStyleSheet(
            "QLabel { background-color: #11111b; color: #6c7086; "
            "border: 1px solid #45475a; border-radius: 4px; }"
        )
        layout.addWidget(self.image_label)

    def set_node(self, node: RosNode) -> None:
        """Attach to a ROS node and begin topic discovery."""
        self._node = node
        self._discover_topics()
        self._discovery_timer.start(5000)

    def detach_node(self) -> None:
        """Detach from the ROS node and stop updates."""
        self._discovery_timer.stop()
        self._destroy_subscription()
        self._node = None
        self.image_label.setText("Ei kuvaa")
        self.combo_topic.clear()
        self.combo_topic.addItem("(ei aihetta)", "")

    def _discover_topics(self) -> None:
        if self._node is None:
            return
        topics = self._node.get_topic_names_and_types()
        image_topics = sorted(
            t for t, types in topics if "sensor_msgs/msg/Image" in types
        )
        current = self.combo_topic.currentData()
        self.combo_topic.blockSignals(True)
        self.combo_topic.clear()
        self.combo_topic.addItem("(ei aihetta)", "")
        for t in image_topics:
            self.combo_topic.addItem(t, t)
        # Restore previous selection if still available
        for i in range(self.combo_topic.count()):
            if self.combo_topic.itemData(i) == current:
                self.combo_topic.setCurrentIndex(i)
                break
        self.combo_topic.blockSignals(False)

    def _on_topic_changed(self, _index: int) -> None:
        self._destroy_subscription()
        topic = self.combo_topic.currentData()
        if not topic or self._node is None:
            self.image_label.setText("Ei kuvaa")
            return
        self._sub = self._node.create_subscription(
            RosImage, topic, self._on_image, 5
        )

    def _destroy_subscription(self) -> None:
        if self._sub is not None and self._node is not None:
            self._node.destroy_subscription(self._sub)
            self._sub = None

    def _on_image(self, msg: RosImage) -> None:
        """ROS callback – runs on the spin thread."""
        qimg = self._ros_image_to_qimage(msg)
        if qimg is not None:
            self._bridge.image_ready.emit(qimg)

    def _update_image(self, qimg: QImage) -> None:
        """Qt slot – runs on the main thread."""
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(pixmap)

    @staticmethod
    def _ros_image_to_qimage(msg: RosImage) -> QImage | None:
        """Convert a sensor_msgs/Image to QImage without cv_bridge."""
        encoding = msg.encoding
        h, w = msg.height, msg.width

        if encoding in ("bgr8", "rgb8"):
            data = np.frombuffer(msg.data, dtype=np.uint8).reshape(h, w, 3)
            if encoding == "bgr8":
                data = data[:, :, ::-1].copy()
            return QImage(data.data, w, h, w * 3, QImage.Format.Format_RGB888).copy()

        if encoding == "mono8":
            data = np.frombuffer(msg.data, dtype=np.uint8).reshape(h, w)
            return QImage(
                data.data, w, h, w, QImage.Format.Format_Grayscale8
            ).copy()

        if encoding in ("bgra8", "rgba8"):
            data = np.frombuffer(msg.data, dtype=np.uint8).reshape(h, w, 4)
            if encoding == "bgra8":
                data = data[:, :, [2, 1, 0, 3]].copy()
            return QImage(
                data.data, w, h, w * 4, QImage.Format.Format_RGBA8888
            ).copy()

        return None
