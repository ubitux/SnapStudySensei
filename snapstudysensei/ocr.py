from manga_ocr import MangaOcr
from PIL import Image, ImageOps, ImageStat


class OCRWrapper:
    def __init__(self):
        self._mocr = MangaOcr()

    def __call__(self, image: Image.Image) -> str:
        image = ImageOps.autocontrast(ImageOps.grayscale(image))
        # Assume the background covers most of the crop, and prefer dark text
        # on a light background.
        if ImageStat.Stat(image).median[0] < 128:
            image = ImageOps.invert(image)
        return self._mocr(image)
