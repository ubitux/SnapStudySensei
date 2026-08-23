import unicodedata

from fugashi import Tagger


def _utf16_length(text: str) -> int:
    """Return the number of UTF-16 code units used by QML string offsets."""
    return len(text.encode("utf-16-le")) // 2


def _is_word(surface: str) -> bool:
    # LMN for letters, marks and numbers
    return bool(surface) and any(unicodedata.category(character)[0] in "LMN" for character in surface)


class Segmenter:
    def __init__(self):
        self._tagger = Tagger()

    def word_span_at(self, text: str, position: int) -> tuple[int, int] | None:
        """Return the QML selection span for the token at a UTF-16 offset."""
        if position < 0 or position >= _utf16_length(text):
            return None

        search_from = 0
        for token in self._tagger(text):
            surface = token.surface
            start = text.find(surface, search_from)
            if start == -1:
                continue

            end = start + len(surface)
            search_from = end
            qml_start = _utf16_length(text[:start])
            qml_end = _utf16_length(text[:end])
            if qml_start <= position < qml_end:
                return (qml_start, qml_end) if _is_word(surface) else None

        return None
