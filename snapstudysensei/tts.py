import tempfile
from pathlib import Path
from typing import Any


class TTSWrapper:
    SAMPLE_RATE = 24_000
    VOICE = "jf_alpha"

    def __init__(self):
        self._tempfile = Path(tempfile.gettempdir()) / "SnapStudySensei.opus"
        self._pipeline: Any | None = None

        # Cache only the last entry
        self._last_key: tuple[str, str, str] | None = None
        self._last_value: Path | None = None

        self._method = "none"
        self.set_method(self._method)

    def set_method(self, method: str):
        self._func = {
            "kokoro-word": self._kokoro_word,
            "kokoro-reading": self._kokoro_reading,
            "none": self._none,
        }[method]
        self._method = method

    def _none(self, word: str, reading: str) -> Path | None:
        return None

    def _get_pipeline(self):
        if self._pipeline is None:
            from kokoro import KPipeline

            self._pipeline = KPipeline(lang_code="j", repo_id="hexgrad/Kokoro-82M")
        return self._pipeline

    def _synthesize(self, text: str) -> Path:
        import soundfile as sf

        generator = self._get_pipeline()(text, voice=self.VOICE)
        result = next(generator, None)
        if result is None or result[2] is None:
            raise RuntimeError("Kokoro did not generate any audio")

        sf.write(self._tempfile, result[2], self.SAMPLE_RATE, format="OGG", subtype="OPUS")
        return self._tempfile

    def _kokoro_word(self, word: str, reading: str) -> Path:
        return self._synthesize(word)

    def _kokoro_reading(self, word: str, reading: str) -> Path:
        return self._synthesize(reading)

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
