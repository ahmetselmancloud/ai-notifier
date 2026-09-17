# Mobil Eşlikçi Uygulama / FCM Push (Faz 2, Alt-Proje 3/3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eşleştirilmiş telefona, masaüstünün gönderdiği her bildirimle birlikte gerçek
bir Firebase Cloud Messaging (FCM) push bildirimi de gitmesi.

**Architecture:** `devices` tablosuna `fcm_token` eklenir; masaüstü bunu dar kapsamlı bir
Postgres RPC fonksiyonuyla okur (anon key ile tüm tabloyu dökmeyi engellemek için).
`NotificationDispatcher` artık tek bildirim yerine bir liste (Windows Toast + Push)
kullanır. Mobil uygulama (Expo + gerçek Firebase native SDK) e-posta ile giriş yapıp
FCM token'ını kaydeder.

**Tech Stack:** `firebase-admin` (Python), Expo + `@react-native-firebase/messaging`
(gerçek native Firebase SDK — Expo Go YETMEZ, development build gerekir),
`@supabase/supabase-js`.

## Global Constraints

- Platform: sadece Android (spec bölüm 1).
- FCM token okuma, anon key ile tüm tabloyu ifşa ETMEZ — sadece dar kapsamlı RPC
  fonksiyonu üzerinden, `desktop_instance_id` ile (spec bölüm 2).
- Masaüstü, eşleşme/token yoksa SESSİZCE hiçbir şey yapmaz, hata fırlatmaz (spec bölüm 5).
- Windows Toast + Push HER ZAMAN birlikte gönderilir — "boşta kalma" tespiti YOK
  (brainstorming kararı, spec bölüm 1).
- Bu görev, önceki alt-projelerden farklı olarak gerçek native mobil derleme
  (Android SDK/Gradle, Expo development build) içerir — kurulum adımları önceki
  Next.js/web işinden daha uzun sürebilir ve iteratif düzeltme gerekebilir.

---

## Dosya Yapısı

```
D:\ai-notifier\
  sql\
    migration_fcm_token.sql
  src\ai_notifier\
    core\
      dispatcher.py           # DEĞİŞECEK: tek notifier yerine liste
      service.py               # DEĞİŞECEK: PushNotifier eklenecek
    notifications\
      push.py                  # YENİ
  tests\
    test_dispatcher.py         # DEĞİŞECEK
    test_push.py                # YENİ
  mobile\                       # YENİ: Expo projesi
    app.json
    App.tsx
    package.json
    lib\
      supabase.ts
```

---

### Task 1: Supabase Şema Değişikliği (fcm_token + RPC)

**Files:**
- Create: `sql\migration_fcm_token.sql`

- [ ] **Step 1: Migrasyon dosyasını yaz**

```sql
alter table devices add column if not exists fcm_token text;

create policy "authenticated can update own device fcm token"
  on devices for update
  to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create or replace function get_fcm_token_for_desktop(p_desktop_instance_id text)
returns text
language sql
security definer
set search_path = public
as $$
  select fcm_token from devices where desktop_instance_id = p_desktop_instance_id limit 1;
$$;

grant execute on function get_fcm_token_for_desktop(text) to anon;
```

- [ ] **Step 2: Supabase SQL Editor'de çalıştır**

Supabase Dashboard → SQL Editor → yapıştır → Run.

Expected: Hatasız tamamlanır.

- [ ] **Step 3: Doğrula**

Table Editor → `devices` tablosunda `fcm_token` sütununun göründüğünü doğrula.
Database → Functions → `get_fcm_token_for_desktop` fonksiyonunun listede olduğunu doğrula.

- [ ] **Step 4: Commit**

```bash
git add sql/migration_fcm_token.sql
git commit -m "chore: add fcm_token column and secure lookup RPC to Supabase schema"
```

---

### Task 2: `push.py` (TDD)

**Files:**
- Create: `src\ai_notifier\notifications\push.py`
- Test: `tests\test_push.py`

**Interfaces:**
- Consumes: `CONFIG_PATH`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `load_config` (mevcut,
  `ai_notifier.core.pairing`), `NotificationSender` (mevcut,
  `ai_notifier.notifications.base`)
- Produces:
  - `get_fcm_token_for_desktop(desktop_instance_id: str, http_post=requests.post) -> str | None`
  - `PushNotifier(NotificationSender)`:
    `__init__(self, config_path: Path = CONFIG_PATH, send_fn=..., http_post=requests.post)`
    `.send(title: str, message: str) -> None`

- [ ] **Step 1: Başarısız testleri yaz**

`tests\test_push.py`:
```python
from ai_notifier.notifications.push import PushNotifier, get_fcm_token_for_desktop


def test_get_fcm_token_for_desktop_returns_token_when_present():
    def fake_post(url, headers, json, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return "fcm-token-abc"

        return FakeResponse()

    assert get_fcm_token_for_desktop("instance-1", http_post=fake_post) == "fcm-token-abc"


def test_get_fcm_token_for_desktop_returns_none_when_null():
    def fake_post(url, headers, json, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return None

        return FakeResponse()

    assert get_fcm_token_for_desktop("instance-1", http_post=fake_post) is None


def test_push_notifier_does_nothing_without_desktop_instance_id(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    calls = []

    notifier = PushNotifier(
        config_path=config_path, send_fn=lambda t, m, tok: calls.append((t, m, tok))
    )
    notifier.send("title", "message")

    assert calls == []


def test_push_notifier_does_nothing_without_fcm_token(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"desktop_instance_id": "instance-1"}', encoding="utf-8")
    calls = []

    def fake_post(url, headers, json, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return None

        return FakeResponse()

    notifier = PushNotifier(
        config_path=config_path,
        send_fn=lambda t, m, tok: calls.append((t, m, tok)),
        http_post=fake_post,
    )
    notifier.send("title", "message")

    assert calls == []


def test_push_notifier_sends_when_token_found(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"desktop_instance_id": "instance-1"}', encoding="utf-8")
    calls = []

    def fake_post(url, headers, json, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return "fcm-token-xyz"

        return FakeResponse()

    notifier = PushNotifier(
        config_path=config_path,
        send_fn=lambda t, m, tok: calls.append((t, m, tok)),
        http_post=fake_post,
    )
    notifier.send("Claude Desktop", "YZ işlemini tamamladı.")

    assert calls == [("Claude Desktop", "YZ işlemini tamamladı.", "fcm-token-xyz")]
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_push.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: `firebase-admin` bağımlılığını ekle**

`pyproject.toml`'daki `dependencies` listesine ekle:
```toml
dependencies = [
    "pywinauto>=0.6.9",
    "pywin32>=306",
    "websockets==12.0",
    "requests>=2.31",
    "pystray>=0.19.5",
    "Pillow>=10.4",
    "firebase-admin>=6.5",
]
```

```powershell
cd D:\ai-notifier
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

- [ ] **Step 4: `push.py` dosyasını yaz**

Aşağıdaki `FIREBASE_SERVICE_ACCOUNT_PATH` değerini Task 4'te gerçek bir dosya yoluyla
güncelleyeceksin.

```python
from pathlib import Path

import requests

from ai_notifier.core.pairing import CONFIG_PATH, SUPABASE_ANON_KEY, SUPABASE_URL, load_config
from ai_notifier.notifications.base import NotificationSender

FIREBASE_SERVICE_ACCOUNT_PATH = "REPLACE_WITH_PATH_TO_YOUR_FIREBASE_SERVICE_ACCOUNT_JSON"

_firebase_app = None


def _headers() -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }


def get_fcm_token_for_desktop(desktop_instance_id: str, http_post=requests.post) -> str | None:
    response = http_post(
        f"{SUPABASE_URL}/rest/v1/rpc/get_fcm_token_for_desktop",
        headers=_headers(),
        json={"p_desktop_instance_id": desktop_instance_id},
        timeout=10,
    )
    response.raise_for_status()
    token = response.json()
    return token or None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def _send_fcm_message(title: str, body: str, token: str) -> None:
    from firebase_admin import messaging

    _get_firebase_app()
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=token,
    )
    messaging.send(message)


class PushNotifier(NotificationSender):
    def __init__(
        self,
        config_path: Path = CONFIG_PATH,
        send_fn=_send_fcm_message,
        http_post=requests.post,
    ):
        self._config_path = config_path
        self._send_fn = send_fn
        self._http_post = http_post

    def send(self, title: str, message: str) -> None:
        config = load_config(self._config_path)
        desktop_instance_id = config.get("desktop_instance_id")
        if not desktop_instance_id:
            return

        token = get_fcm_token_for_desktop(desktop_instance_id, http_post=self._http_post)
        if not token:
            return

        self._send_fn(title, message, token)
```

- [ ] **Step 5: Testlerin geçtiğini doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_push.py -v
```

Expected: 5 test PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ai_notifier/notifications/push.py tests/test_push.py pyproject.toml
git commit -m "feat: add PushNotifier (FCM via secure RPC lookup)"
```

---

### Task 3: `NotificationDispatcher` Çoklu Bildirim Desteği + Servise Bağlama

**Files:**
- Modify: `src\ai_notifier\core\dispatcher.py`
- Modify: `tests\test_dispatcher.py`
- Modify: `src\ai_notifier\core\service.py`

**Interfaces:**
- Consumes: `PushNotifier` (Task 2)
- Produces: `NotificationDispatcher(notifiers: list[NotificationSender], stability_threshold: int = 2)`
  (imza değişti: `notifier` yerine `notifiers` listesi)

- [ ] **Step 1: Mevcut testleri yeni imzaya güncelle**

`tests\test_dispatcher.py` — HER `NotificationDispatcher(notifier=notifier, ...)`
çağrısını `NotificationDispatcher(notifiers=[notifier], ...)` ile değiştir (dosyadaki
4 test fonksiyonunun hepsinde).

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_dispatcher.py -v
```

Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'notifiers'`

- [ ] **Step 3: `dispatcher.py`'ı güncelle**

```python
from ai_notifier.core.decision_engine import DecisionEngine
from ai_notifier.core.messages import state_to_notification
from ai_notifier.notifications.base import NotificationSender
from ai_notifier.sensors.base import SensorState


class NotificationDispatcher:
    """Herhangi bir kaynaktan (masaüstü polling, tarayıcı WebSocket) gelen ham
    durumları DecisionEngine üzerinden geçirip onaylanan değişiklikleri TÜM
    bildirim kanallarına (Windows Toast + Push) birlikte gönderir."""

    def __init__(
        self, notifiers: list[NotificationSender], stability_threshold: int = 2
    ):
        self._engine = DecisionEngine(stability_threshold=stability_threshold)
        self._notifiers = notifiers

    def submit(self, source_name: str, raw_state: SensorState) -> None:
        confirmed = self._engine.submit_reading(source_name, raw_state)
        if confirmed is None:
            return
        notification = state_to_notification(source_name, confirmed)
        if notification is None:
            return
        title, message = notification
        for notifier in self._notifiers:
            notifier.send(title, message)
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_dispatcher.py -v
```

Expected: 4 test PASS.

- [ ] **Step 5: `service.py`'ı `PushNotifier` kullanacak şekilde güncelle**

`src\ai_notifier\core\service.py` içindeki `_run()` fonksiyonunda:
```python
    dispatcher = NotificationDispatcher(notifier=WindowsToastNotifier())
```
satırını şununla değiştir:
```python
    dispatcher = NotificationDispatcher(
        notifiers=[WindowsToastNotifier(), PushNotifier()]
    )
```

Dosyanın en üstündeki import bloğuna ekle:
```python
from ai_notifier.notifications.push import PushNotifier
```

- [ ] **Step 6: Tüm test paketinin hâlâ geçtiğini doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: Tüm testler PASS.

- [ ] **Step 7: Commit**

```bash
git add src/ai_notifier/core/dispatcher.py tests/test_dispatcher.py src/ai_notifier/core/service.py
git commit -m "feat: support multiple notification channels, wire in PushNotifier"
```

---

### Task 4: Firebase Projesi Kurulumu (Selman) + `push.py` Güncelleme

**Files:**
- Modify: `src\ai_notifier\notifications\push.py`

Bu görev tamamen Selman'ın kendi Firebase/Google hesabında yapması gereken kurulum
adımlarıdır — Claude bunları yapamaz (hesap/OAuth işlemleri).

- [ ] **Step 1: Firebase projesi oluştur**

[Firebase Console](https://console.firebase.google.com) → "Add project" → proje adı
(örn. `ai-notifier`) → Google Analytics'i kapatabilirsin (gerekli değil) → oluştur.

- [ ] **Step 2: Android uygulaması ekle**

Firebase Console → proje → "Add app" → Android ikonu → paket adı (örn.
`com.selman.ainotifier` — Task 5'te aynı paket adı `mobile/app.json`'da kullanılacak)
→ kaydet → **`google-services.json` dosyasını indir**, `D:\ai-notifier\mobile\`
klasörüne (Task 5'te oluşturulacak) koymak üzere sakla.

- [ ] **Step 3: Servis hesabı anahtarı indir**

Firebase Console → proje ayarları (dişli ikonu) → "Service accounts" sekmesi →
"Generate new private key" → indirilen JSON dosyasını `D:\ai-notifier\` dışında,
güvenli bir yerde sakla (örn. `%APPDATA%\ai-notifier\firebase-service-account.json`)
— bu dosya ASLA git'e commit edilmemeli (gizli anahtar içeriyor).

- [ ] **Step 4: `push.py`'daki yolu güncelle**

`src\ai_notifier\notifications\push.py` içinde:
```python
FIREBASE_SERVICE_ACCOUNT_PATH = "REPLACE_WITH_PATH_TO_YOUR_FIREBASE_SERVICE_ACCOUNT_JSON"
```
satırını gerçek dosya yoluyla güncelle, örn:
```python
FIREBASE_SERVICE_ACCOUNT_PATH = r"C:\Users\ahmet\AppData\Roaming\ai-notifier\firebase-service-account.json"
```

- [ ] **Step 5: Commit**

```bash
git add src/ai_notifier/notifications/push.py
git commit -m "chore: point PushNotifier at real Firebase service account path"
```

(Servis hesabı JSON dosyasının kendisi commit EDİLMEZ.)

---

### Task 5: Mobil Uygulama (Expo + Gerçek Firebase Messaging)

**Files:**
- Create: `mobile\package.json`, `mobile\app.json`, `mobile\App.tsx`, `mobile\lib\supabase.ts`
- Modify: `mobile\google-services.json` (Task 4'te indirilen dosya buraya konur)

Bu görev gerçek bir Android native derlemesi içerir; Expo Go YETMEZ. Adımlar
sırasıyla ilerlerken beklenmeyen bir hata çıkarsa (Android SDK/Gradle sürüm
uyumsuzlukları çok yaygındır), hatayı okuyup düzeltmek gerekecektir — bu normaldir.

- [ ] **Step 1: Expo projesini gerçek CLI ile oluştur**

```powershell
cd D:\ai-notifier
npx create-expo-app@latest mobile --template blank-typescript
cd mobile
npx expo install expo-dev-client
npx expo install @react-native-firebase/app @react-native-firebase/messaging
npm install @supabase/supabase-js
```

- [ ] **Step 2: `google-services.json`'ı yerleştir**

Task 4 Step 2'de indirdiğin dosyayı `D:\ai-notifier\mobile\google-services.json`
olarak kopyala.

- [ ] **Step 3: `app.json`'ı güncelle**

```json
{
  "expo": {
    "name": "AI-Notifier",
    "slug": "ai-notifier-mobile",
    "version": "0.1.0",
    "scheme": "ainotifier",
    "android": {
      "package": "com.selman.ainotifier",
      "googleServicesFile": "./google-services.json"
    },
    "plugins": [
      "@react-native-firebase/app",
      "expo-dev-client"
    ]
  }
}
```

(`android.package` değerini Task 4 Step 2'de Firebase'e girdiğin paket adıyla
BİREBİR aynı yap.)

- [ ] **Step 4: `lib/supabase.ts` dosyasını yaz**

```typescript
import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  "https://wvhlikiiqrculbpvphxk.supabase.co",
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind2aGxpa2lpcXJjdWxicHZwaHhrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk1ODM4NzMsImV4cCI6MjEwNTE1OTg3M30.f2Qztv7xssStlPUAmGGCPAsHYuo-cv9aImBDpThmQs0"
);
```

- [ ] **Step 5: `App.tsx` dosyasını yaz**

```tsx
import { useEffect, useState } from "react";
import { SafeAreaView, Text, TextInput, Button, StyleSheet } from "react-native";
import messaging from "@react-native-firebase/messaging";
import { supabase } from "./lib/supabase";

export default function App() {
  const [email, setEmail] = useState("");
  const [linkSent, setLinkSent] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    const { data: authListener } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        if (!session) return;
        await registerFcmToken(session.user.id);
      }
    );

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        registerFcmToken(session.user.id);
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, []);

  async function registerFcmToken(userId: string) {
    const token = await messaging().getToken();
    const { error } = await supabase
      .from("devices")
      .update({ fcm_token: token })
      .eq("user_id", userId);

    setStatus(error ? "FCM token kaydedilemedi: " + error.message : "Bağlandı, bildirimler açık.");
  }

  async function sendMagicLink() {
    await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: "ainotifier://login-callback" },
    });
    setLinkSent(true);
  }

  if (status) {
    return (
      <SafeAreaView style={styles.container}>
        <Text>{status}</Text>
      </SafeAreaView>
    );
  }

  if (linkSent) {
    return (
      <SafeAreaView style={styles.container}>
        <Text>E-postana bir giriş linki gönderdik. Linke tıkla.</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>AI-Notifier</Text>
      <TextInput
        style={styles.input}
        placeholder="E-posta adresiniz"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
      />
      <Button title="Giriş linki gönder" onPress={sendMagicLink} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 24 },
  title: { fontSize: 24, marginBottom: 16, textAlign: "center" },
  input: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 12, marginBottom: 12 },
});
```

- [ ] **Step 6: Supabase Auth'a mobil redirect URL'sini ekle**

Supabase Dashboard → Authentication → URL Configuration → "Redirect URLs" listesine
`ainotifier://login-callback` ekle.

- [ ] **Step 7: Development build oluştur ve çalıştır**

```powershell
cd D:\ai-notifier\mobile
npx expo prebuild --platform android
npx expo run:android
```

(Android cihazın USB ile bağlı ve "USB hata ayıklama" açık olmalı, veya bir Android
emülatörü çalışıyor olmalı.)

- [ ] **Step 8: Manuel doğrulama**

Uygulama telefonda açılınca e-posta gir, giriş linkine tıkla, "Bağlandı, bildirimler
açık." mesajını gör. Supabase Table Editor → `devices` tablosunda ilgili satırda
`fcm_token` sütununun dolu olduğunu doğrula.

- [ ] **Step 9: Commit**

```bash
git add mobile/package.json mobile/app.json mobile/App.tsx mobile/lib mobile/google-services.json
git commit -m "feat: add Expo mobile app with magic link login and FCM registration"
```

---

### Task 6: Uçtan Uca Gerçek Push Testi

**Files:** (kod değişikliği yok, sadece doğrulama)

- [ ] **Step 1: Tüm Python test paketini çalıştır**

```powershell
cd D:\ai-notifier
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: Tüm testler PASS.

- [ ] **Step 2: Masaüstü servisini başlat**

```powershell
.venv\Scripts\python.exe -m ai_notifier.core.service
```

- [ ] **Step 3: Gerçek bir Claude Desktop yanıtı tetikle**

Claude Desktop'ta (veya bu oturumda) bir mesaj gönder, yanıtın tamamlanmasını bekle.

- [ ] **Step 4: Telefonda push bildirimini doğrula**

Telefonun ekranında (uygulama kapalıyken bile) gerçek bir FCM push bildirimi
göründüğünü doğrula — "Claude Desktop: YZ işlemini tamamladı." Bu, Faz 1'de bilinen
masaüstü Toast sınırından (paketleme gerektiriyor) BAĞIMSIZ bir kanal — push'un
çalışması için masaüstü paketlemesi beklemek gerekmiyor.
