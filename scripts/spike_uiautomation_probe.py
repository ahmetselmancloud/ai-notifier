"""Faz 0 doğrulama betiği.

Kullanım: Claude Desktop veya ChatGPT Desktop'ı aç, ardından:
    python scripts/spike_uiautomation_probe.py "Claude"
    python scripts/spike_uiautomation_probe.py "ChatGPT"

Betik, pencereyi bulup içindeki tüm buton/metin elemanlarını 5 kez art arda
(1 saniye arayla) okur ve her denemede kaç eleman bulduğunu basar. Bu, kaç
retry gerektiğini ve pencere minimize edildiğinde okumanın bozulup
bozulmadığını gözlemlemek içindir.
"""

import sys
import time

import uiautomation as auto


def probe_window(window_title_substring: str, attempts: int = 5, delay_seconds: float = 1.0) -> None:
    window = auto.WindowControl(searchDepth=1, SubName=window_title_substring)
    if not window.Exists(maxSearchSeconds=3):
        print(f"Pencere bulunamadı: '{window_title_substring}' alt dizesini içeren pencere yok.")
        return

    print(f"Pencere bulundu: {window.Name} (Handle: {window.NativeWindowHandle})")

    for attempt in range(1, attempts + 1):
        buttons = [
            child.Name
            for child in _walk(window)
            if child.ControlTypeName == "ButtonControl" and child.Name
        ]
        print(f"Deneme {attempt}/{attempts}: {len(buttons)} buton bulundu -> {buttons}")
        time.sleep(delay_seconds)


def _walk(control, max_depth: int = 6, _depth: int = 0):
    yield control
    if _depth >= max_depth:
        return
    for child in control.GetChildren():
        yield from _walk(child, max_depth=max_depth, _depth=_depth + 1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Kullanım: python scripts/spike_uiautomation_probe.py <pencere-başlığı-alt-dizesi>")
        sys.exit(1)

    probe_window(sys.argv[1])
