from manga_ocr import MangaOcr
from PIL import Image


class OCRWrapper:
    def __init__(self):
        self._mocr = MangaOcr()

    def __call__(self, image: Image.Image) -> str:
        return self._mocr(image)
