from PIL import Image

from ai_notifier.core.tray import create_icon_image


def test_create_icon_image_returns_correct_size_image():
    image = create_icon_image()
    assert isinstance(image, Image.Image)
    assert image.size == (64, 64)
