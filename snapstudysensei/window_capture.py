from PySide6.QtCore import Property, QObject, Qt, Signal, Slot
from PySide6.QtGui import QWindow
from PySide6.QtMultimedia import QVideoFrame, QVideoFrameFormat, QVideoSink
from PySide6.QtQml import QmlElement

QML_IMPORT_NAME = "SnapStudySensei"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
class WindowCaptureProducer(QObject):
    widChanged = Signal()
    videoSinkChanged = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._wid = None
        self._video_sink = None

    def _get_wid(self) -> int | None:
        return self._wid

    def _set_wid(self, wid: int | None):
        self._wid = wid
        self.widChanged.emit()

    wid = Property(int, _get_wid, _set_wid, notify=widChanged)

    def _get_videoSink(self) -> QVideoSink:
        assert self._video_sink is not None
        return self._video_sink

    def _set_videoSink(self, video_sink: QVideoSink):
        self._video_sink = video_sink

    videoSink = Property(QObject, _get_videoSink, _set_videoSink, notify=videoSinkChanged)

    @Slot()
    def refresh(self):
        if self._wid is None or self._video_sink is None:
            return

        window = QWindow.fromWinId(self._wid)
        pixmap = window.screen().grabWindow(window.winId())
        pixmap = pixmap.scaled(240, 180, Qt.KeepAspectRatio)
        image = pixmap.toImage()

        pixel_format = QVideoFrameFormat.pixelFormatFromImageFormat(image.format())
        frame_format = QVideoFrameFormat(image.size(), pixel_format)
        frame = QVideoFrame(frame_format)

        # Memcpy from image to video frame
        frame.map(QVideoFrame.WriteOnly)
        dst = frame.bits(0)
        src = image.bits()
        dst_linesize = frame.bytesPerLine(0)
        src_linesize = image.bytesPerLine()
        copy_linesize = min(dst_linesize, src_linesize)
        for y in range(image.height()):
            dst_start = y * dst_linesize
            src_start = y * src_linesize
            dst[dst_start : dst_start + copy_linesize] = src[src_start : src_start + copy_linesize]
        frame.unmap()

        self._video_sink.setVideoFrame(frame)
