import sys
import tempfile
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Property, QObject, QRect, QRectF, QSize, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtMultimedia import QVideoFrame, QVideoFrameFormat, QVideoSink
from PySide6.QtQml import QmlElement, QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider

from snapstudysensei.anki import AnkiConnect, AnkiNote
from snapstudysensei.dic import JDictionary
from snapstudysensei.ocr import OCRWrapper
from snapstudysensei.tts import TTSWrapper
from snapstudysensei.windows_list import WindowsList

QML_IMPORT_NAME = "SnapStudySensei"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
class WindowCaptureProducer(QObject):
    widChanged = Signal()
    videoSinkChanged = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        app = QGuiApplication.instance()
        self._wid = None
        self._screen = app.primaryScreen()
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

        pixmap = self._screen.grabWindow(self._wid)
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


class SnapshotProvider(QQuickImageProvider):
    snapshotTaken = Signal(QPixmap)

    def __init__(self, app):
        super().__init__(QQuickImageProvider.Pixmap)
        self._screen = app.primaryScreen()

    def requestPixmap(self, id: str, size: QSize, requestedSize: QSize) -> QPixmap:
        wid = int(id)
        pixmap = self._screen.grabWindow(wid)

        self.snapshotTaken.emit(pixmap)

        width = min(pixmap.width(), 640)
        height = min(pixmap.height(), 480)
        pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio)
        return pixmap


class SnapStudySensei:
    def __init__(self, app, ocr: OCRWrapper, dic: JDictionary, tts: TTSWrapper):
        self._ocr = ocr
        self._dic = dic
        self._tts = tts

        self._include_screenshot = True
        self._audio = None
        self._anki = AnkiConnect()
        self._tempdir = Path(tempfile.gettempdir())

        self._snapshot_provider = SnapshotProvider(app)
        self._snapshot_provider.snapshotTaken.connect(self._snapshot_taken)
        self._snapshot = None

        self._engine = QQmlApplicationEngine()
        self._engine.addImageProvider("snapshot", self._snapshot_provider)

        # Init capture windows list
        self._wid = None
        self._winlist = WindowsList()
        self._update_windows_list_model()  # make sure the model is set before loading the QML

        # Load QML
        qml_file = Path(__file__).parent / "main.qml"
        self._engine.load(qml_file)
        root_objects = self._engine.rootObjects()
        if not root_objects:
            sys.exit(-1)
        self._window = root_objects[0]

        # Fill all records grabbed from Anki
        notes = self._anki.list_notes()
        records = [note.get_qml_record() for note in notes]
        self._window.add_records(records)

        # Connect signals from the QML
        self._window.requestWindowsListRefresh.connect(self._windows_list_refresh)
        self._window.selectionMade.connect(self._selection_made)
        self._window.wordSelected.connect(self._word_selected)
        self._window.requestRecordAdd.connect(self._record_add)
        self._window.recordRemoved.connect(self._record_remove)
        self._window.includeScreenshotToggled.connect(self._include_screenshot_toggled)
        self._window.audioSourceChanged.connect(self._audio_source_changed)

    @Slot(str, str, str, str)
    def _record_add(self, sentence: str, word: str, reading: str, meaning: str):
        if self._snapshot is not None and self._include_screenshot:
            picture = Image.fromqpixmap(self._snapshot) if self._snapshot else None
            picture_path = self._tempdir / "SnapStudySensei.png"
            picture.save(picture_path)
        else:
            picture_path = None

        note = AnkiNote(
            word=word,
            context_picture=picture_path,
            context_sentence=sentence,
            word_reading=reading,
            word_glossary=meaning,
            word_audio=self._audio,
        )
        note = self._anki.add_note(note)
        self._window.add_records([note.get_qml_record()])

    @Slot(str)
    def _record_remove(self, record_id: str):
        anki_id = int(record_id)
        self._anki.remove_note(anki_id)

    def _update_windows_list_model(self) -> list[dict[str, str | int]]:
        """Rebuild the list of windows entirely"""
        self._wid = None
        windows = self._winlist()
        windows_list_model = [dict(title=title, wid=wid) for wid, (title, _) in windows.items()]
        self._engine.rootContext().setContextProperty("windowsListModel", windows_list_model)
        return windows_list_model

    @Slot(int)
    def _windows_list_refresh(self, wid: int):
        windows_list_model = self._update_windows_list_model()

        # Check if the previously selected window can still be found in the new windows set
        if wid is not None:
            ids = [window["wid"] for window in windows_list_model]
            self._window.set_capture_window(ids.index(wid))

    @Slot(str, str, str)
    def _audio_source_changed(self, audio_source: str, word: str, reading: str):
        self._tts.set_method(audio_source)
        try:
            source = self._tts(word, reading)
        except Exception:
            print("unable to grab audio", file=sys.stderr)
            source = None
        self._audio = source
        self._window.stop_audio()
        if source is not None:
            self._window.play_audio(source.as_posix())

    @Slot(bool)
    def _include_screenshot_toggled(self, value: bool):
        self._include_screenshot = value

    @Slot(QPixmap)
    def _snapshot_taken(self, pixmap: QPixmap):
        self._snapshot = pixmap

    @Slot(QRectF)
    def _selection_made(self, rectf: QRectF):
        if not self._snapshot:
            return

        snapshot = self._snapshot
        rect = QRect(
            int(rectf.x() * snapshot.width()),
            int(rectf.y() * snapshot.height()),
            int(rectf.width() * snapshot.width()),
            int(rectf.height() * snapshot.height()),
        )
        pixmap = self._snapshot.copy(rect)
        image = Image.fromqpixmap(pixmap)

        text = self._ocr(image)
        self._window.set_sentence(text.strip())

    @Slot(str)
    def _word_selected(self, word: str):
        info = self._dic(word)
        self._window.set_word_info(info)


def run(ocr: OCRWrapper, dic: JDictionary, tts: TTSWrapper):
    app = QGuiApplication(sys.argv)
    sss = SnapStudySensei(app, ocr, dic, tts)
    ret = app.exec()
    del sss
    sys.exit(ret)
