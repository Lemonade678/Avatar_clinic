"""Shelf-photo checks: is it an image at all, and is it bright enough for the CV model?"""
from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError


MAX_SIDE = 1280  # plenty for counting packages; keeps ~2 years of photos inside Supabase's free 1 GB
JPEG_QUALITY = 80


class PhotoError(ValueError):
    pass


def shrink(content: bytes, max_side: int = MAX_SIDE, quality: int = JPEG_QUALITY) -> bytes:
    """Upright, at most `max_side` px on the long side, re-encoded as JPEG (also drops EXIF such as GPS)."""
    try:
        with Image.open(BytesIO(content)) as img:
            upright = ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise PhotoError("not a readable image") from e
    upright.thumbnail((max_side, max_side))
    out = BytesIO()
    upright.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()


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
