from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPixmap, QWindow
from PySide6.QtQuick import QQuickImageProvider


class SnapshotProvider(QQuickImageProvider):
    snapshotTaken = Signal(QPixmap)

    def __init__(self):
        super().__init__(QQuickImageProvider.Pixmap)

    def requestPixmap(self, id: str, size: QSize, requestedSize: QSize) -> QPixmap:
        wid = int(id)
        window = QWindow.fromWinId(wid)
        pixmap = window.screen().grabWindow(window.winId())

        self.snapshotTaken.emit(pixmap)

        width = min(pixmap.width(), 640)
        height = min(pixmap.height(), 480)
        pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio)
        return pixmap
