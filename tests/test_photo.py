from io import BytesIO

import pytest
from PIL import Image

from stockcount.photo import PhotoError, brightness, is_too_dark


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
