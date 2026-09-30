"""Shelf-photo checks: is it an image at all, and is it bright enough for the CV model?"""
from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageStat, UnidentifiedImageError


class PhotoError(ValueError):
    pass


def brightness(content: bytes) -> float:
    """Mean luminance 0 (black) – 255 (white), computed on a small copy for speed."""
    try:
        with Image.open(BytesIO(content)) as img:
            img.draft("L", (256, 256))  # JPEG fast path: decode straight to a small greyscale
            grey = img.convert("L")
            grey.thumbnail((256, 256))
            return float(ImageStat.Stat(grey).mean[0])
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise PhotoError("not a readable image") from e


def is_too_dark(value: float, minimum: int) -> bool:
    return value < minimum
