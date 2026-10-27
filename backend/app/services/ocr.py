import io
import warnings
from threading import BoundedSemaphore
from PIL import Image, ImageOps, UnidentifiedImageError
import pytesseract
from app.core.config import get_settings

MAX_BYTES = 5 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 12_000_000
ALLOWED_TYPES = {'image/png', 'image/jpeg', 'image/webp'}
_slots = BoundedSemaphore(2)


class OCRUnavailable(Exception):
    pass


def extract_text(data: bytes, content_type: str) -> str:
    if not _slots.acquire(blocking=False):
        raise OCRUnavailable('OCR is busy. Please try again shortly.')
    try:
        return _extract_text(data, content_type)
    finally:
        _slots.release()


def _extract_text(data: bytes, content_type: str) -> str:
    if len(data) > MAX_BYTES:
        raise ValueError('Image exceeds the 5 MB limit.')
    if content_type not in ALLOWED_TYPES:
        raise ValueError('Upload a PNG, JPEG or WEBP image.')
    settings = get_settings()
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in {'PNG', 'JPEG', 'WEBP'}:
                    raise ValueError('The image content does not match a supported format.')
                if source.width * source.height > 12_000_000:
                    raise ValueError('Image exceeds 12 megapixels.')
                source.load()
                image = ImageOps.exif_transpose(source).convert('RGB')
                image.thumbnail((2400, 2400))
                # Rebuild pixels to strip EXIF, comments, ICC and other metadata.
                clean = Image.new('RGB', image.size, 'white')
                clean.paste(image)
                text = pytesseract.image_to_string(clean, lang=settings.ocr_languages, timeout=20)
                clean.close()
                image.close()
        return text.strip()[:10000]
    except pytesseract.TesseractNotFoundError:
        raise OCRUnavailable('OCR is unavailable. Install Tesseract or paste the screenshot text into the message scanner.') from None
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError, OSError):
        raise ValueError('Invalid image or image dimensions exceed the safe limit.') from None
    except RuntimeError:
        raise OCRUnavailable('OCR timed out. Use a smaller screenshot or paste the text.') from None
    except pytesseract.TesseractError:
        raise OCRUnavailable('OCR language data is unavailable. Check OCR_LANGUAGES and the Tesseract installation.') from None
