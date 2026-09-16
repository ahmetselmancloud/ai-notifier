# AI-Notifier MVP (Windows Masaüstü Sensörü) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude Desktop ve ChatGPT Desktop'ın durumunu (üretiyor / bitti / onay bekliyor / hata)
Windows üzerinde arka planda, event-driven UIAutomation ile izleyip Windows Toast bildirimi
gönderen bir Python servisi kurmak.

**Architecture:** `BaseSensor` arayüzünü uygulayan iki adaptör (Claude Desktop, ChatGPT Desktop)
UI Automation olaylarına abone olur, her ham okumayı `DecisionEngine`'e iletir. `DecisionEngine`
ardışık N aynı okuma ile kararlılığı doğrulayıp yalnızca gerçek durum değişikliklerini onaylar.
Onaylanan her değişiklik `messages.py` üzerinden Türkçe bildirim metnine çevrilip
`WindowsToastNotifier` ile gösterilir. Tüm parçalar `core/service.py` içinde asyncio event
loop'unda birbirine bağlanır.

**Tech Stack:** Python 3.11+, `uiautomation` (Windows UI Automation sarmalayıcısı), `win10toast`
(Windows Toast bildirimleri), `pytest` (test).

## Global Constraints

- Platform: yalnızca Windows (spec bölüm 1) — Mac desteği kapsam dışı.
- Hedef uygulamalar: yalnızca Claude Desktop ve ChatGPT Desktop (spec bölüm 1).
- Tespit mekanizması: polling DEĞİL, UI Automation event subscription + hedefe kilitli sorgu +
  debounce/kararlılık kontrolü (spec bölüm 3.2).
- Pencere minimize/arka plandayken de tespit çalışmalı (kullanıcının zorunlu gereksinimi, spec
  bölüm 3.2).
- `UNKNOWN` durumunda asla bildirim gönderilmez (spec bölüm 3.2, madde 4).
- Ekran görüntüsü/OCR/vision KULLANILMAZ (spec bölüm 3.2 giriş paragrafı).
- Proje konumu: `D:\ai-notifier`, bağımsız git deposu (spec bölüm 7).
- Sensör adaptörleri ileride (web/Ollama/Mac) genişleyebilecek şekilde `BaseSensor` arayüzü
  üzerinden soyutlanır (spec bölüm 3.1).

---

## Dosya Yapısı

```
D:\ai-notifier\
  pyproject.toml
  README.md
  .gitignore
  src\ai_notifier\
    __init__.py
    sensors\
      __init__.py
      base.py              # SensorState enum, BaseSensor arayüzü
      claude_desktop.py    # ClaudeDesktopSensor
      chatgpt_desktop.py   # ChatGPTDesktopSensor
    core\
      __init__.py
      decision_engine.py   # Debounce/kararlılık state machine
      messages.py          # SensorState -> (title, message) çevirisi
      service.py           # asyncio wiring: sensörler -> engine -> notifier
    notifications\
      __init__.py
      base.py               # NotificationSender arayüzü
      windows_toast.py       # WindowsToastNotifier
  scripts\
    spike_uiautomation_probe.py   # Faz 0 doğrulama betiği
  tests\
    test_scaffolding.py
    test_decision_engine.py
    test_messages.py
    test_windows_toast.py
    test_sensors_base.py
```

---

### Task 1: Proje İskeleti

**Files:**
- Create: `D:\ai-notifier\pyproject.toml`
- Create: `D:\ai-notifier\.gitignore`
- Create: `D:\ai-notifier\README.md`
- Create: `D:\ai-notifier\src\ai_notifier\__init__.py`
- Create: `D:\ai-notifier\src\ai_notifier\sensors\__init__.py`
- Create: `D:\ai-notifier\src\ai_notifier\core\__init__.py`
- Create: `D:\ai-notifier\src\ai_notifier\notifications\__init__.py`
- Test: `D:\ai-notifier\tests\test_scaffolding.py`

**Interfaces:**
- Produces: `ai_notifier` paketinin import edilebilir olması (sonraki tüm task'lar bu paket
  altına kod ekler).

- [ ] **Step 1: `pyproject.toml` dosyasını oluştur**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "ai-notifier"
version = "0.1.0"
description = "Yapay zeka asistanlari icin evrensel durum takip ve bildirim sistemi (Windows MVP)"
requires-python = ">=3.11"
dependencies = [
    "uiautomation>=2.0.20",
    "win10toast>=0.9",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: `.gitignore` dosyasını oluştur**

```
__pycache__/
*.pyc
.venv/
*.egg-info/
build/
dist/
```

- [ ] **Step 3: `README.md` dosyasını oluştur**

```markdown
# AI-Notifier (PingAI) — Windows MVP

Claude Desktop ve ChatGPT Desktop'ın durumunu arka planda izleyip Windows Toast
bildirimi gönderen servis.

## Kurulum

\`\`\`powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
\`\`\`

## Test

\`\`\`powershell
pytest
\`\`\`
```

- [ ] **Step 4: Paket klasörlerini ve boş `__init__.py` dosyalarını oluştur**

`src\ai_notifier\__init__.py`:
```python
__version__ = "0.1.0"
```

`src\ai_notifier\sensors\__init__.py`:
```python
```

`src\ai_notifier\core\__init__.py`:
```python
```

`src\ai_notifier\notifications\__init__.py`:
```python
```

- [ ] **Step 5: İskeletin çalıştığını doğrulayan testi yaz**

`tests\test_scaffolding.py`:
```python
def test_package_is_importable():
    import ai_notifier

    assert ai_notifier.__version__ == "0.1.0"
```

- [ ] **Step 6: Sanal ortamı kur ve paketi kurup testi çalıştır**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest tests/test_scaffolding.py -v
```

Expected: `test_package_is_importable` PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore README.md src tests
git commit -m "chore: scaffold ai-notifier package structure"
```

---

### Task 2: `SensorState` ve `BaseSensor` Arayüzü

**Files:**
- Create: `src\ai_notifier\sensors\base.py`
- Test: `tests\test_sensors_base.py`

**Interfaces:**
- Produces:
  - `SensorState` enum: `GENERATING`, `DONE`, `WAITING_APPROVAL`, `ERROR`, `UNKNOWN`
  - `BaseSensor` abstract class:
    - `name: str` (attribute, örn. `"claude_desktop"`)
    - `start(self, on_state_changed: Callable[[str, SensorState], None]) -> None`
    - `stop(self) -> None`

- [ ] **Step 1: Başarısız testi yaz**

`tests\test_sensors_base.py`:
```python
import pytest

from ai_notifier.sensors.base import BaseSensor, SensorState


def test_sensor_state_has_expected_members():
    assert SensorState.GENERATING.value == "generating"
    assert SensorState.DONE.value == "done"
    assert SensorState.WAITING_APPROVAL.value == "waiting_approval"
    assert SensorState.ERROR.value == "error"
    assert SensorState.UNKNOWN.value == "unknown"


def test_base_sensor_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseSensor()


def test_base_sensor_subclass_must_implement_start_and_stop():
    class IncompleteSensor(BaseSensor):
        name = "incomplete"

    with pytest.raises(TypeError):
        IncompleteSensor()


def test_base_sensor_subclass_with_full_implementation_can_be_instantiated():
    class DummySensor(BaseSensor):
        name = "dummy"

        def start(self, on_state_changed):
            self._callback = on_state_changed

        def stop(self):
            pass

    sensor = DummySensor()
    assert sensor.name == "dummy"
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

```powershell
pytest tests/test_sensors_base.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ai_notifier.sensors.base'`

- [ ] **Step 3: `base.py` dosyasını yaz**

```python
from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable


class SensorState(Enum):
    GENERATING = "generating"
    DONE = "done"
    WAITING_APPROVAL = "waiting_approval"
    ERROR = "error"
    UNKNOWN = "unknown"


class BaseSensor(ABC):
    """Tek bir YZ masaüstü uygulamasını izleyen sensör adaptörlerinin ortak arayüzü.

    Bir adaptör, hedef pencerede UI Automation olayına her tetiklendiğinde
    hedefe kilitli bir sorgu yapar ve ham okumayı (henüz debounce edilmemiş)
    on_state_changed callback'i ile bildirir. Kararlılık/debounce mantığı
    burada DEĞİL, DecisionEngine'de uygulanır.
    """

    name: str

    @abstractmethod
    def start(self, on_state_changed: Callable[[str, SensorState], None]) -> None:
        """İzlemeyi başlatır; UI Automation olayına her tetiklendiğinde
        on_state_changed(self.name, state) çağrılır."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """UI Automation olay aboneliğini kaldırır, kaynakları temizler."""
        raise NotImplementedError
```

- [ ] **Step 4: Testin geçtiğini doğrula**

```powershell
pytest tests/test_sensors_base.py -v
```

Expected: 4 test PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_notifier/sensors/base.py tests/test_sensors_base.py
git commit -m "feat: add SensorState enum and BaseSensor interface"
```

---

### Task 3: `DecisionEngine` (Debounce/Kararlılık Mantığı)

**Files:**
- Create: `src\ai_notifier\core\decision_engine.py`
- Test: `tests\test_decision_engine.py`

**Interfaces:**
- Consumes: `SensorState` (Task 2, `ai_notifier.sensors.base`)
- Produces:
  - `DecisionEngine(stability_threshold: int = 2)`
  - `.submit_reading(sensor_name: str, state: SensorState) -> SensorState | None`
    - Ardışık `stability_threshold` kez aynı ham okuma gelirse ve bu, o sensör için son
      onaylanmış durumdan farklıysa, yeni durumu döner (bildirime dönüştürülecek).
    - `SensorState.UNKNOWN` okuması gelirse: o sensörün bekleyen okuma geçmişini sıfırlar,
      her zaman `None` döner (asla onaylanmaz/bildirilmez).
    - Aksi halde `None` döner.

- [ ] **Step 1: Başarısız testleri yaz**

`tests\test_decision_engine.py`:
```python
from ai_notifier.core.decision_engine import DecisionEngine
from ai_notifier.sensors.base import SensorState


def test_confirms_after_stability_threshold_consecutive_reads():
    engine = DecisionEngine(stability_threshold=2)

    assert engine.submit_reading("claude", SensorState.GENERATING) is None
    assert engine.submit_reading("claude", SensorState.GENERATING) is SensorState.GENERATING


def test_does_not_reconfirm_already_confirmed_state():
    engine = DecisionEngine(stability_threshold=2)
    engine.submit_reading("claude", SensorState.GENERATING)
    engine.submit_reading("claude", SensorState.GENERATING)

    assert engine.submit_reading("claude", SensorState.GENERATING) is None


def test_single_flaky_read_does_not_confirm():
    engine = DecisionEngine(stability_threshold=2)

    assert engine.submit_reading("claude", SensorState.DONE) is None


def test_unknown_reading_resets_pending_streak_and_never_confirms():
    engine = DecisionEngine(stability_threshold=2)
    engine.submit_reading("claude", SensorState.DONE)

    assert engine.submit_reading("claude", SensorState.UNKNOWN) is None
    # DONE'un tek okuması UNKNOWN tarafından sıfırlandı, bu yüzden DONE'un
    # tekrar 2 kez art arda okunması gerekir.
    assert engine.submit_reading("claude", SensorState.DONE) is None
    assert engine.submit_reading("claude", SensorState.DONE) is SensorState.DONE


def test_sensors_are_tracked_independently():
    engine = DecisionEngine(stability_threshold=2)
    engine.submit_reading("claude", SensorState.GENERATING)
    engine.submit_reading("claude", SensorState.GENERATING)

    assert engine.submit_reading("chatgpt", SensorState.GENERATING) is None


def test_changing_confirmed_state_requires_new_stability_streak():
    engine = DecisionEngine(stability_threshold=2)
    engine.submit_reading("claude", SensorState.GENERATING)
    engine.submit_reading("claude", SensorState.GENERATING)

    assert engine.submit_reading("claude", SensorState.DONE) is None
    assert engine.submit_reading("claude", SensorState.DONE) is SensorState.DONE
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

```powershell
pytest tests/test_decision_engine.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ai_notifier.core.decision_engine'`

- [ ] **Step 3: `decision_engine.py` dosyasını yaz**

```python
from dataclasses import dataclass, field

from ai_notifier.sensors.base import SensorState


@dataclass
class _SensorHistory:
    pending_state: SensorState | None = None
    pending_count: int = 0
    confirmed_state: SensorState | None = None


class DecisionEngine:
    """Sensörlerden gelen ham okumaları, ardışık N aynı okuma ile
    doğrulanana kadar bildirime dönüştürmeyen kararlılık/debounce motoru."""

    def __init__(self, stability_threshold: int = 2):
        self._stability_threshold = stability_threshold
        self._histories: dict[str, _SensorHistory] = {}

    def submit_reading(
        self, sensor_name: str, state: SensorState
    ) -> SensorState | None:
        history = self._histories.setdefault(sensor_name, _SensorHistory())

        if state is SensorState.UNKNOWN:
            history.pending_state = None
            history.pending_count = 0
            return None

        if state == history.pending_state:
            history.pending_count += 1
        else:
            history.pending_state = state
            history.pending_count = 1

        if history.pending_count < self._stability_threshold:
            return None

        if state == history.confirmed_state:
            return None

        history.confirmed_state = state
        return state
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```powershell
pytest tests/test_decision_engine.py -v
```

Expected: 6 test PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_notifier/core/decision_engine.py tests/test_decision_engine.py
git commit -m "feat: add DecisionEngine debounce/stability logic"
```

---

### Task 4: Bildirim Metinleri (`messages.py`)

**Files:**
- Create: `src\ai_notifier\core\messages.py`
- Test: `tests\test_messages.py`

**Interfaces:**
- Consumes: `SensorState` (Task 2)
- Produces: `state_to_notification(sensor_name: str, state: SensorState) -> tuple[str, str]`
  → `(title, message)`. `GENERATING` ve `UNKNOWN` için `None` döner (bildirime dönüşmez;
  `GENERATING` ara durumdur, `UNKNOWN` zaten `DecisionEngine` tarafından hiç buraya
  gelmeyecektir ama savunmacı olarak burada da ele alınır).

- [ ] **Step 1: Başarısız testi yaz**

`tests\test_messages.py`:
```python
from ai_notifier.core.messages import state_to_notification
from ai_notifier.sensors.base import SensorState


def test_done_maps_to_completion_message():
    title, message = state_to_notification("Claude Desktop", SensorState.DONE)

    assert title == "Claude Desktop"
    assert message == "YZ işlemini tamamladı."


def test_waiting_approval_maps_to_approval_message():
    title, message = state_to_notification("ChatGPT Desktop", SensorState.WAITING_APPROVAL)

    assert title == "ChatGPT Desktop"
    assert message == "YZ onay veya seçim bekliyor!"


def test_error_maps_to_error_message():
    title, message = state_to_notification("Claude Desktop", SensorState.ERROR)

    assert title == "Claude Desktop"
    assert message == "Bağlantı hatası oluştu, müdahale gerekli."


def test_generating_and_unknown_have_no_notification():
    assert state_to_notification("Claude Desktop", SensorState.GENERATING) is None
    assert state_to_notification("Claude Desktop", SensorState.UNKNOWN) is None
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

```powershell
pytest tests/test_messages.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ai_notifier.core.messages'`

- [ ] **Step 3: `messages.py` dosyasını yaz**

```python
from ai_notifier.sensors.base import SensorState

_MESSAGES: dict[SensorState, str] = {
    SensorState.DONE: "YZ işlemini tamamladı.",
    SensorState.WAITING_APPROVAL: "YZ onay veya seçim bekliyor!",
    SensorState.ERROR: "Bağlantı hatası oluştu, müdahale gerekli.",
}


def state_to_notification(
    sensor_name: str, state: SensorState
) -> tuple[str, str] | None:
    message = _MESSAGES.get(state)
    if message is None:
        return None
    return sensor_name, message
```

- [ ] **Step 4: Testin geçtiğini doğrula**

```powershell
pytest tests/test_messages.py -v
```

Expected: 4 test PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_notifier/core/messages.py tests/test_messages.py
git commit -m "feat: add sensor state to notification text mapping"
```

---

### Task 5: `NotificationSender` Arayüzü ve `WindowsToastNotifier`

**Files:**
- Create: `src\ai_notifier\notifications\base.py`
- Create: `src\ai_notifier\notifications\windows_toast.py`
- Test: `tests\test_windows_toast.py`

**Interfaces:**
- Produces:
  - `NotificationSender` abstract class: `send(self, title: str, message: str) -> None`
  - `WindowsToastNotifier(NotificationSender)`: `__init__(self, toaster=None)`,
    test edilebilirlik için `toaster` enjekte edilebilir (varsayılan: gerçek
    `win10toast.ToastNotifier()`).

- [ ] **Step 1: Başarısız testi yaz**

`tests\test_windows_toast.py`:
```python
from ai_notifier.notifications.windows_toast import WindowsToastNotifier


class FakeToaster:
    def __init__(self):
        self.calls = []

    def show_toast(self, title, msg, duration, threaded):
        self.calls.append((title, msg, duration, threaded))


def test_send_calls_show_toast_with_title_and_message():
    fake_toaster = FakeToaster()
    notifier = WindowsToastNotifier(toaster=fake_toaster)

    notifier.send("Claude Desktop", "YZ işlemini tamamladı.")

    assert fake_toaster.calls == [
        ("Claude Desktop", "YZ işlemini tamamladı.", 5, True)
    ]
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

```powershell
pytest tests/test_windows_toast.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ai_notifier.notifications.windows_toast'`

- [ ] **Step 3: `base.py` dosyasını yaz**

`src\ai_notifier\notifications\base.py`:
```python
from abc import ABC, abstractmethod


class NotificationSender(ABC):
    @abstractmethod
    def send(self, title: str, message: str) -> None:
        raise NotImplementedError
```

- [ ] **Step 4: `windows_toast.py` dosyasını yaz**

`src\ai_notifier\notifications\windows_toast.py`:
```python
from win10toast import ToastNotifier

from ai_notifier.notifications.base import NotificationSender


class WindowsToastNotifier(NotificationSender):
    def __init__(self, toaster=None):
        self._toaster = toaster if toaster is not None else ToastNotifier()

    def send(self, title: str, message: str) -> None:
        self._toaster.show_toast(title, message, duration=5, threaded=True)
```

- [ ] **Step 5: Testin geçtiğini doğrula**

```powershell
pytest tests/test_windows_toast.py -v
```

Expected: 1 test PASS.

- [ ] **Step 6: Gerçek bir toast bildirimi ile manuel doğrula**

```powershell
python -c "from ai_notifier.notifications.windows_toast import WindowsToastNotifier; WindowsToastNotifier().send('AI-Notifier Testi', 'Bu bir deneme bildirimidir.')"
```

Expected: Windows ekranında gerçek bir toast bildirimi görünür.

- [ ] **Step 7: Commit**

```bash
git add src/ai_notifier/notifications tests/test_windows_toast.py
git commit -m "feat: add Windows Toast notification sender"
```

---

### Task 6: Faz 0 — UIAutomation Doğrulama Betiği (spike)

**Files:**
- Create: `scripts\spike_uiautomation_probe.py`
- Create: `docs\superpowers\plans\2026-09-16-faz0-findings.md` (bulgular buraya elle yazılacak)

Bu görev, spec'in Faz 0 bölümünde tanımlanan teknik doğrulamadır. Otomatik test değildir —
gerçek Claude Desktop ve ChatGPT Desktop pencerelerine karşı elle çalıştırılıp gözlemlenir.

**Interfaces:**
- Produces: `probe_window(window_title_substring: str, target_names: list[str]) -> None` —
  sonraki task'larda (7, 8) sensör adaptörlerinin hangi arama deseninin (Name/ControlType,
  kaç deneme) güvenilir olduğunu belirlemek için kullanılır.

- [ ] **Step 1: Betiği yaz**

`scripts\spike_uiautomation_probe.py`:
```python
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
        elements = window.GetChildren()
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
```

- [ ] **Step 2: Bağımlılıkları kur ve betiği Claude Desktop açıkken çalıştır**

```powershell
pip install -e ".[dev]"
python scripts/spike_uiautomation_probe.py "Claude"
```

Gözlemle: her denemede bulunan buton sayısı ve isimleri tutarlı mı, ilk denemede boş/eksik
mi geliyor (bu oturumda Claude Code penceresinde gözlemlendiği gibi)?

- [ ] **Step 3: Aynı betiği pencere minimize edilmişken çalıştır**

Claude Desktop'ı minimize et (veya başka bir pencerenin arkasına al), betiği tekrar çalıştır.

```powershell
python scripts/spike_uiautomation_probe.py "Claude"
```

Gözlemle: minimize/arka plan durumunda da butonlar okunabiliyor mu?

- [ ] **Step 4: Aynı testleri ChatGPT Desktop için tekrarla**

```powershell
python scripts/spike_uiautomation_probe.py "ChatGPT"
```

- [ ] **Step 5: Bulguları yaz**

`docs\superpowers\plans\2026-09-16-faz0-findings.md` dosyasını oluştur ve şunları elle
doldur (gerçek gözlemlere göre):

```markdown
# Faz 0 Bulguları

## Claude Desktop
- Kararlı okuma için gereken deneme sayısı: <buraya yaz>
- "Stop" / "Devam Et" gibi butonların gerçek Name değerleri: <buraya yaz>
- Minimize/arka plandayken okuma çalışıyor mu: <evet/hayır + gözlem>

## ChatGPT Desktop
- Kararlı okuma için gereken deneme sayısı: <buraya yaz>
- İlgili buton Name değerleri: <buraya yaz>
- Minimize/arka plandayken okuma çalışıyor mu: <evet/hayır + gözlem>
```

Bu dosyadaki değerler Task 7 ve Task 8'deki adaptörlerin sabitlerini (retry sayısı, aranacak
buton isimleri) belirler.

- [ ] **Step 6: Commit**

```bash
git add scripts/spike_uiautomation_probe.py docs/superpowers/plans/2026-09-16-faz0-findings.md
git commit -m "chore: add Faz 0 UIAutomation validation spike and findings"
```

---

### Task 7: `ClaudeDesktopSensor` Adaptörü

**Files:**
- Create: `src\ai_notifier\sensors\claude_desktop.py`

**Interfaces:**
- Consumes:
  - `BaseSensor`, `SensorState` (Task 2)
  - Task 6'nın `docs/superpowers/plans/2026-09-16-faz0-findings.md` dosyasındaki buton
    isimleri ve retry sayısı
- Produces: `ClaudeDesktopSensor(BaseSensor)` — `name = "Claude Desktop"`

Not: Bu adaptör gerçek bir Windows GUI'ye bağımlı olduğu için birim testi yazılmaz (spec
bölüm 5'teki test stratejisiyle tutarlı). Doğrulama manuel senaryo testiyle yapılır.

- [ ] **Step 1: Adaptörü yaz**

Task 6'nın bulgularında tespit edilen buton isimlerini (`STOP_BUTTON_NAME`,
`APPROVAL_BUTTON_NAMES`) ve retry sayısını (`STABLE_READ_ATTEMPTS`) aşağıdaki
placeholder değerlerin yerine gerçek bulgularla güncelle:

`src\ai_notifier\sensors\claude_desktop.py`:
```python
import time
from typing import Callable

import uiautomation as auto

from ai_notifier.sensors.base import BaseSensor, SensorState

# Task 6 (Faz 0) bulgularına göre güncellenecek sabitler.
STOP_BUTTON_NAME = "Stop"
APPROVAL_BUTTON_NAMES = ("Devam Et", "Allow", "İzin Ver")
ERROR_TEXT_MARKERS = ("Network Error", "Regenerate")
STABLE_READ_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 0.3


class ClaudeDesktopSensor(BaseSensor):
    name = "Claude Desktop"

    def __init__(self):
        self._on_state_changed: Callable[[str, SensorState], None] | None = None
        self._window = None

    def start(self, on_state_changed: Callable[[str, SensorState], None]) -> None:
        self._on_state_changed = on_state_changed
        self._window = auto.WindowControl(searchDepth=1, SubName="Claude")
        auto.AddAutomationEventHandler(
            auto.AutomationEventId.StructureChangedEvent,
            self._window,
            auto.TreeScope.TreeScope_Subtree,
            None,
            self._on_ui_event,
        )

    def stop(self) -> None:
        auto.RemoveAllEventHandlers()
        self._window = None
        self._on_state_changed = None

    def _on_ui_event(self, sender, event_id) -> None:
        state = self._read_state_with_retry()
        if self._on_state_changed is not None:
            self._on_state_changed(self.name, state)

    def _read_state_with_retry(self) -> SensorState:
        last_state = SensorState.UNKNOWN
        for _ in range(STABLE_READ_ATTEMPTS):
            last_state = self._read_state_once()
            if last_state is not SensorState.UNKNOWN:
                return last_state
            time.sleep(RETRY_DELAY_SECONDS)
        return last_state

    def _read_state_once(self) -> SensorState:
        if self._window is None or not self._window.Exists(maxSearchSeconds=0):
            return SensorState.UNKNOWN

        button_names = [
            child.Name
            for child in self._window.GetChildren()
            if child.ControlTypeName == "ButtonControl" and child.Name
        ]

        if any(marker in " ".join(button_names) for marker in ERROR_TEXT_MARKERS):
            return SensorState.ERROR
        if any(name in APPROVAL_BUTTON_NAMES for name in button_names):
            return SensorState.WAITING_APPROVAL
        if STOP_BUTTON_NAME in button_names:
            return SensorState.GENERATING
        return SensorState.DONE
```

- [ ] **Step 2: Claude Desktop açıkken manuel senaryo testi yap**

```powershell
python -c "
from ai_notifier.sensors.claude_desktop import ClaudeDesktopSensor
import time

def on_change(name, state):
    print(f'{name}: {state}')

sensor = ClaudeDesktopSensor()
sensor.start(on_change)
print('Dinleniyor... Claude Desktop'ta bir mesaj gönder.')
time.sleep(60)
sensor.stop()
"
```

Senaryoları elle tetikle ve konsolda doğru sırayla `GENERATING` → `DONE` (veya
`WAITING_APPROVAL`) geldiğini doğrula:
1. Bir mesaj gönder, yanıt üretilirken durumu gözlemle.
2. Yanıt tamamlanınca durumu gözlemle.
3. (Varsa) bir araç onayı isteyen bir istekte durumu gözlemle.

- [ ] **Step 3: Commit**

```bash
git add src/ai_notifier/sensors/claude_desktop.py
git commit -m "feat: add ClaudeDesktopSensor adapter"
```

---

### Task 8: `ChatGPTDesktopSensor` Adaptörü

**Files:**
- Create: `src\ai_notifier\sensors\chatgpt_desktop.py`

**Interfaces:**
- Consumes: `BaseSensor`, `SensorState` (Task 2); Task 6'nın ChatGPT Desktop bulguları
- Produces: `ChatGPTDesktopSensor(BaseSensor)` — `name = "ChatGPT Desktop"`

- [ ] **Step 1: Adaptörü yaz (Task 7 ile aynı desen, ChatGPT Desktop'a özel sabitlerle)**

Task 6'nın ChatGPT Desktop bulgularına göre `STOP_BUTTON_NAME`, `APPROVAL_BUTTON_NAMES`,
`ERROR_TEXT_MARKERS` değerlerini güncelle:

`src\ai_notifier\sensors\chatgpt_desktop.py`:
```python
import time
from typing import Callable

import uiautomation as auto

from ai_notifier.sensors.base import BaseSensor, SensorState

# Task 6 (Faz 0) bulgularına göre güncellenecek sabitler.
STOP_BUTTON_NAME = "Stop generating"
APPROVAL_BUTTON_NAMES = ("Continue", "Allow", "Devam Et")
ERROR_TEXT_MARKERS = ("Network Error", "Regenerate")
STABLE_READ_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 0.3


class ChatGPTDesktopSensor(BaseSensor):
    name = "ChatGPT Desktop"

    def __init__(self):
        self._on_state_changed: Callable[[str, SensorState], None] | None = None
        self._window = None

    def start(self, on_state_changed: Callable[[str, SensorState], None]) -> None:
        self._on_state_changed = on_state_changed
        self._window = auto.WindowControl(searchDepth=1, SubName="ChatGPT")
        auto.AddAutomationEventHandler(
            auto.AutomationEventId.StructureChangedEvent,
            self._window,
            auto.TreeScope.TreeScope_Subtree,
            None,
            self._on_ui_event,
        )

    def stop(self) -> None:
        auto.RemoveAllEventHandlers()
        self._window = None
        self._on_state_changed = None

    def _on_ui_event(self, sender, event_id) -> None:
        state = self._read_state_with_retry()
        if self._on_state_changed is not None:
            self._on_state_changed(self.name, state)

    def _read_state_with_retry(self) -> SensorState:
        last_state = SensorState.UNKNOWN
        for _ in range(STABLE_READ_ATTEMPTS):
            last_state = self._read_state_once()
            if last_state is not SensorState.UNKNOWN:
                return last_state
            time.sleep(RETRY_DELAY_SECONDS)
        return last_state

    def _read_state_once(self) -> SensorState:
        if self._window is None or not self._window.Exists(maxSearchSeconds=0):
            return SensorState.UNKNOWN

        button_names = [
            child.Name
            for child in self._window.GetChildren()
            if child.ControlTypeName == "ButtonControl" and child.Name
        ]

        if any(marker in " ".join(button_names) for marker in ERROR_TEXT_MARKERS):
            return SensorState.ERROR
        if any(name in APPROVAL_BUTTON_NAMES for name in button_names):
            return SensorState.WAITING_APPROVAL
        if STOP_BUTTON_NAME in button_names:
            return SensorState.GENERATING
        return SensorState.DONE
```

- [ ] **Step 2: ChatGPT Desktop açıkken Task 7'deki gibi manuel senaryo testi yap**

```powershell
python -c "
from ai_notifier.sensors.chatgpt_desktop import ChatGPTDesktopSensor
import time

def on_change(name, state):
    print(f'{name}: {state}')

sensor = ChatGPTDesktopSensor()
sensor.start(on_change)
print('Dinleniyor... ChatGPT Desktop'ta bir mesaj gönder.')
time.sleep(60)
sensor.stop()
"
```

- [ ] **Step 3: Commit**

```bash
git add src/ai_notifier/sensors/chatgpt_desktop.py
git commit -m "feat: add ChatGPTDesktopSensor adapter"
```

---

### Task 9: Core Servis Bağlantısı (uçtan uca)

**Files:**
- Create: `src\ai_notifier\core\service.py`

**Interfaces:**
- Consumes:
  - `ClaudeDesktopSensor`, `ChatGPTDesktopSensor` (Task 7, 8)
  - `DecisionEngine` (Task 3)
  - `state_to_notification` (Task 4)
  - `WindowsToastNotifier` (Task 5)
- Produces: `run()` fonksiyonu — servisin giriş noktası.

- [ ] **Step 1: `service.py` dosyasını yaz**

```python
import time

from ai_notifier.core.decision_engine import DecisionEngine
from ai_notifier.core.messages import state_to_notification
from ai_notifier.notifications.windows_toast import WindowsToastNotifier
from ai_notifier.sensors.chatgpt_desktop import ChatGPTDesktopSensor
from ai_notifier.sensors.claude_desktop import ClaudeDesktopSensor

SENSORS = [ClaudeDesktopSensor(), ChatGPTDesktopSensor()]


def run() -> None:
    engine = DecisionEngine(stability_threshold=2)
    notifier = WindowsToastNotifier()

    def on_state_changed(sensor_name, raw_state) -> None:
        confirmed = engine.submit_reading(sensor_name, raw_state)
        if confirmed is None:
            return
        notification = state_to_notification(sensor_name, confirmed)
        if notification is None:
            return
        title, message = notification
        notifier.send(title, message)

    for sensor in SENSORS:
        sensor.start(on_state_changed)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for sensor in SENSORS:
            sensor.stop()


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Claude Desktop ve ChatGPT Desktop açıkken uçtan uca manuel test yap**

```powershell
python -m ai_notifier.core.service
```

Senaryo: her iki uygulamada da sırayla bir mesaj gönder, yanıt tamamlandığında gerçek bir
Windows Toast bildirimi göründüğünü doğrula. Ardından bir pencereyi minimize edip aynı
senaryoyu tekrarla — bildirimin yine geldiğini doğrula (spec'in zorunlu gereksinimi).

- [ ] **Step 3: Commit**

```bash
git add src/ai_notifier/core/service.py
git commit -m "feat: wire sensors, decision engine and notifier into service entrypoint"
```

---

## Self-Review Notları

- **Spec kapsaması:** Faz 0 doğrulama (Task 6), BaseSensor/adaptör deseni (Task 2, 7, 8),
  event-subscription + hedefe kilitli sorgu + retry (Task 7, 8), debounce/kararlılık
  (Task 3), UNKNOWN'da bildirim yok (Task 3 testleri), Windows Toast (Task 5), uçtan uca
  wiring (Task 9) — spec'in 2-6. bölümleri kapsandı. Performans (bölüm 4) tasarım
  kararlarına (event-driven, hedefe kilitli sorgu) yansıdı, ayrı bir task gerektirmiyor.
- **Placeholder taraması:** Task 7/8'deki buton isimleri Task 6'nın bulgularıyla
  güncellenecek şekilde açıkça işaretlendi (gerçek kod var, "TODO" değil).
- **Tip tutarlılığı:** `SensorState`, `BaseSensor.start/stop` imzası, `DecisionEngine.submit_reading`
  dönüş tipi, `state_to_notification` dönüş tipi tüm task'larda tutarlı kullanıldı.
