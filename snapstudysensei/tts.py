import tempfile
import urllib
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlretrieve

from gtts import gTTS


class TTSWrapper:
    def __init__(self):
        self._tempfile = Path(tempfile.gettempdir()) / "SnapStudySensei.mp3"

        # Cache only the last entry
        self._last_key: tuple[str, str, str] | None = None
        self._last_value: Path | None = None

        self._method = "none"
        self.set_method(self._method)

    def set_method(self, method: str):
        self._func = {
            "google-kanji": self._google_kanji,
            "google-reading": self._google_reading,
            "pod101": self._pod101,
            "none": self._none,
        }[method]
        self._method = method

    def _none(self, word: str, reading: str) -> Path | None:
        return None

    def _google_kanji(self, word: str, reading: str) -> Path | None:
        tts = gTTS(word, lang="ja")
        tts.save(self._tempfile)
        return self._tempfile

    def _google_reading(self, word: str, reading: str) -> Path | None:
        tts = gTTS(reading, lang="ja")
        tts.save(self._tempfile)
        return self._tempfile

    def _pod101(self, word: str, reading: str) -> Path | None:
        word = quote(word)
        reading = quote(reading)
        url = f"https://assets.languagepod101.com/dictionary/japanese/audiomp3.php?kanji={word}&kana={reading}"
        urlretrieve(url, self._tempfile)
        return self._tempfile

    def __call__(self, word: str, reading: str) -> Path | None:
        if not reading:
            reading = word
        key = (self._method, word, reading)
        if self._last_key is not None and self._last_key == key:
            return self._last_value
        ret = self._func(word, reading)
        self._last_key = key
        self._last_value = ret
        return ret
