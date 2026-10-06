from io import BytesIO

import pytest
from PIL import Image

from stockcount.photo import PhotoError, brightness, is_too_dark, shrink


def jpeg(grey: int, size=(64, 48)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, (grey, grey, grey)).save(buf, format="JPEG")
    return buf.getvalue()


def test_brightness_of_a_dark_and_a_bright_photo():
    assert brightness(jpeg(20)) < 30
    assert brightness(jpeg(200)) > 190


def test_too_dark_uses_the_configured_minimum():
    assert is_too_dark(brightness(jpeg(20)), minimum=60)
    assert not is_too_dark(brightness(jpeg(120)), minimum=60)


def test_not_an_image_is_rejected():
    with pytest.raises(PhotoError):
        brightness(b"definitely not a jpeg")


def big_photo(size=(2560, 1920), orientation=None) -> bytes:
    buf = BytesIO()
    img = Image.effect_noise(size, 64).convert("RGB")  # noisy like a real photo, so JPEG can't cheat
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    img.save(buf, format="JPEG", quality=95, exif=exif)
    return buf.getvalue()


def test_shrink_keeps_the_long_side_at_1280_and_cuts_the_size():
    original = big_photo()
    small = shrink(original)
    with Image.open(BytesIO(small)) as img:
        assert img.format == "JPEG" and max(img.size) == 1280
    assert len(small) < len(original) / 4


def test_shrink_turns_phone_photos_upright():
    # EXIF orientation 6 = the phone was held upright: pixels are stored sideways
    small = shrink(big_photo(size=(400, 200), orientation=6))
    with Image.open(BytesIO(small)) as img:
        assert img.size == (200, 400)


def test_shrink_leaves_small_photos_small():
    with Image.open(BytesIO(shrink(jpeg(120)))) as img:
        assert img.size == (64, 48)


def test_shrink_rejects_non_images():
    with pytest.raises(PhotoError):
        shrink(b"not a photo")
