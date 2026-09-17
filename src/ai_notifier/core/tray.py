from typing import Callable

import pystray
from PIL import Image, ImageDraw


def create_icon_image() -> Image.Image:
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, size - 4, size - 4), fill=(255, 106, 61, 255))
    return image


def build_tray_icon(
    on_pair: Callable[[], None], on_quit: Callable[[], None]
) -> pystray.Icon:
    def _on_pair(icon, item):
        on_pair()

    def _on_quit(icon, item):
        on_quit()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Cihaz Eşleştir", _on_pair),
        pystray.MenuItem("Çıkış", _on_quit),
    )
    return pystray.Icon("AI-Notifier", create_icon_image(), "AI-Notifier", menu)
