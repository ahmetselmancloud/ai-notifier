# Cihaz Eşleştirme / Auth (Faz 2, Alt-Proje 2/3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Masaüstü servisinin bir eşleştirme kodu üretip tarayıcıda göstermesi, kullanıcının
telefonuyla bu kodu (QR ile) tarayıp e-posta sihirli linkiyle giriş yaparak eşleşmeyi
tamamlaması, masaüstünün eşleşen `user_id`'yi yerel olarak saklaması.

**Architecture:** Supabase (Postgres + Auth) ortak durak; Next.js (Vercel) web arayüzü
`/pair` (masaüstünün açtığı, QR gösteren sayfa) ve `/pair/claim` (telefonun açtığı, giriş+
eşleştirme sayfası) sunar; Python masaüstü tarafı (`core/pairing.py`) kodu üretir, tarayıcıyı
açar, Supabase REST API'sini polling ile sorgular.

**Tech Stack:** Next.js 14 (App Router, TypeScript), `@supabase/supabase-js`, `qrcode`
(npm), Python `requests`, mevcut `ai_notifier` paketi.

## Global Constraints

- Kapsam: SADECE eşleştirme/auth. Mobil uygulamanın kendisi (FCM token kaydı) bu planda
  YOK — alt-proje 3'e bırakılıyor (spec bölüm 1).
- Supabase projesi ve Vercel deployment'ı Selman'ın kendi (restoran-qr'dan ayrı) hesabında
  zaten oluşturuldu: proje URL'si `https://wvhlikiiqrculbpvphxk.supabase.co`.
- Eşleştirme kodu 6 haneli, 10 dakika geçerli (spec bölüm 2/3).
- Giriş yöntemi: SADECE e-posta sihirli link — OAuth/şifre YOK (spec bölüm 1, brainstorming
  kararı).
- `pairing_codes`/`devices` tablo şemaları ve RLS ilkeleri tam olarak spec bölüm 3'teki
  mantığı uygular.
- Next.js kodu repo'nun `web/` alt klasöründe yaşar (Vercel monorepo "Root Directory"
  ayarıyla deploy edilecek) — repo kökü Python paketiyle karışmaz.

---

## Dosya Yapısı

```
D:\ai-notifier\
  sql\
    migration_device_pairing.sql       # YENİ: Supabase SQL Editor'de elle çalıştırılır
  src\ai_notifier\core\
    pairing.py                          # YENİ
  tests\
    test_pairing.py                     # YENİ
  web\                                   # YENİ: Next.js uygulaması
    package.json
    tsconfig.json
    next.config.js
    .env.local.example
    .gitignore
    app\
      layout.tsx
      page.tsx
      pair\
        page.tsx
        claim\
          page.tsx
    lib\
      supabase.ts
```

---

### Task 1: Supabase Şema Migrasyonu (SQL)

**Files:**
- Create: `sql\migration_device_pairing.sql`

Bu görev otomatik test içermez — gerçek Supabase projesine karşı elle çalıştırılıp
doğrulanır (spec bölüm 6, "gerçek Supabase entegrasyonu manuel doğrulanır").

- [ ] **Step 1: Migrasyon dosyasını yaz**

`sql\migration_device_pairing.sql`:
```sql
create table if not exists pairing_codes (
  code text primary key,
  desktop_instance_id text not null,
  status text not null default 'pending' check (status in ('pending', 'claimed')),
  claimed_by_user_id uuid references auth.users(id),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null
);

create table if not exists devices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  desktop_instance_id text not null,
  paired_at timestamptz not null default now()
);

alter table pairing_codes enable row level security;
alter table devices enable row level security;

-- anon (masaüstü servisi): bekleyen bir eşleştirme kodu oluşturabilir
create policy "anon can insert pending pairing codes"
  on pairing_codes for insert
  to anon
  with check (status = 'pending' and claimed_by_user_id is null);

-- anon: kodun durumunu okuyabilir (kod zaten rastgele/gizli, kısa ömürlü)
create policy "anon can read pairing codes"
  on pairing_codes for select
  to anon
  using (true);

-- authenticated (telefon): bekleyen, süresi dolmamış bir kodu claim edebilir
create policy "authenticated users can claim pending codes"
  on pairing_codes for update
  to authenticated
  using (status = 'pending' and expires_at > now())
  with check (status = 'claimed' and claimed_by_user_id = auth.uid());

-- authenticated: kendi cihaz kaydını ekleyebilir/okuyabilir
create policy "users can insert their own device"
  on devices for insert
  to authenticated
  with check (user_id = auth.uid());

create policy "users can read their own devices"
  on devices for select
  to authenticated
  using (user_id = auth.uid());
```

- [ ] **Step 2: Supabase SQL Editor'de çalıştır**

Supabase projesi (`https://wvhlikiiqrculbpvphxk.supabase.co`) → sol menüden "SQL Editor"
→ yeni sorgu → yukarıdaki dosyanın tam içeriğini yapıştır → "Run".

Expected: "Success. No rows returned" veya benzeri, hata YOK.

- [ ] **Step 3: Tabloların oluştuğunu doğrula**

Supabase Dashboard → "Table Editor" → `pairing_codes` ve `devices` tablolarının listede
göründüğünü doğrula.

- [ ] **Step 4: Commit**

```bash
git add sql/migration_device_pairing.sql
git commit -m "chore: add Supabase migration for device pairing tables"
```

---

### Task 2: Python `pairing.py` (TDD)

**Files:**
- Create: `src\ai_notifier\core\pairing.py`
- Test: `tests\test_pairing.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces:
  - `generate_pairing_code() -> str`
  - `get_or_create_desktop_instance_id(config_path: Path) -> str`
  - `load_config(config_path: Path) -> dict`
  - `save_config(config_path: Path, config: dict) -> None`
  - `request_pairing_code(desktop_instance_id: str, http_post=requests.post) -> str`
  - `check_pairing_status(code: str, http_get=requests.get) -> str | None`
  - `run_pairing_flow(...) -> str | None` (manuel doğrulanır, birim testi yok)

- [ ] **Step 1: `requests` bağımlılığını ekle**

`pyproject.toml`'daki `dependencies` listesine ekle:
```toml
dependencies = [
    "pywinauto>=0.6.9",
    "pywin32>=306",
    "websockets==12.0",
    "requests>=2.31",
]
```

```powershell
cd D:\ai-notifier
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

- [ ] **Step 2: Başarısız testleri yaz**

`tests\test_pairing.py`:
```python
from ai_notifier.core.pairing import (
    check_pairing_status,
    generate_pairing_code,
    get_or_create_desktop_instance_id,
    request_pairing_code,
)


def test_generate_pairing_code_has_expected_length_and_charset():
    code = generate_pairing_code()
    assert len(code) == 6
    assert code.isalnum()
    assert code == code.upper()


def test_generate_pairing_code_is_random():
    codes = {generate_pairing_code() for _ in range(20)}
    assert len(codes) > 1


def test_get_or_create_desktop_instance_id_creates_and_persists(tmp_path):
    config_path = tmp_path / "config.json"

    first = get_or_create_desktop_instance_id(config_path)
    second = get_or_create_desktop_instance_id(config_path)

    assert first == second
    assert config_path.exists()


def test_request_pairing_code_posts_pending_row_and_returns_code():
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["json"] = json

        class FakeResponse:
            def raise_for_status(self):
                pass

        return FakeResponse()

    code = request_pairing_code("instance-123", http_post=fake_post)

    assert len(code) == 6
    assert captured["json"]["desktop_instance_id"] == "instance-123"
    assert captured["json"]["status"] == "pending"
    assert captured["json"]["code"] == code
    assert "pairing_codes" in captured["url"]


def test_check_pairing_status_returns_none_when_pending():
    def fake_get(url, headers, params, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return [{"status": "pending", "claimed_by_user_id": None}]

        return FakeResponse()

    assert check_pairing_status("A3F9K2", http_get=fake_get) is None


def test_check_pairing_status_returns_user_id_when_claimed():
    def fake_get(url, headers, params, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return [{"status": "claimed", "claimed_by_user_id": "user-abc"}]

        return FakeResponse()

    assert check_pairing_status("A3F9K2", http_get=fake_get) == "user-abc"


def test_check_pairing_status_returns_none_when_code_not_found():
    def fake_get(url, headers, params, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return []

        return FakeResponse()

    assert check_pairing_status("UNKNOWN", http_get=fake_get) is None
```

- [ ] **Step 3: Testlerin başarısız olduğunu doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_pairing.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ai_notifier.core.pairing'`

- [ ] **Step 4: `pairing.py` dosyasını yaz**

Aşağıdaki `SUPABASE_ANON_KEY` ve `PAIRING_WEB_URL` değerlerini Task 6'da gerçek
değerlerle güncelleyeceksin (Task 6 Step 1).

```python
import json
import os
import random
import string
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

SUPABASE_URL = "https://wvhlikiiqrculbpvphxk.supabase.co"
SUPABASE_ANON_KEY = "REPLACE_WITH_YOUR_SUPABASE_ANON_KEY"
PAIRING_WEB_URL = "REPLACE_WITH_YOUR_VERCEL_URL/pair"

CONFIG_PATH = Path(os.environ.get("APPDATA", ".")) / "ai-notifier" / "config.json"

POLL_INTERVAL_SECONDS = 2
CODE_TTL_MINUTES = 10


def _headers() -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def save_config(config_path: Path, config: dict) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def get_or_create_desktop_instance_id(config_path: Path) -> str:
    config = load_config(config_path)
    if "desktop_instance_id" in config:
        return config["desktop_instance_id"]
    instance_id = str(uuid.uuid4())
    config["desktop_instance_id"] = instance_id
    save_config(config_path, config)
    return instance_id


def generate_pairing_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=6))


def request_pairing_code(desktop_instance_id: str, http_post=requests.post) -> str:
    code = generate_pairing_code()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=CODE_TTL_MINUTES)).isoformat()
    response = http_post(
        f"{SUPABASE_URL}/rest/v1/pairing_codes",
        headers={**_headers(), "Prefer": "return=minimal"},
        json={
            "code": code,
            "desktop_instance_id": desktop_instance_id,
            "status": "pending",
            "expires_at": expires_at,
        },
        timeout=10,
    )
    response.raise_for_status()
    return code


def check_pairing_status(code: str, http_get=requests.get) -> str | None:
    """Kod eşleşmişse claimed_by_user_id'yi döner; henüz eşleşmemişse veya
    bulunamamışsa None döner."""
    response = http_get(
        f"{SUPABASE_URL}/rest/v1/pairing_codes",
        headers=_headers(),
        params={"code": f"eq.{code}", "select": "status,claimed_by_user_id"},
        timeout=10,
    )
    response.raise_for_status()
    rows = response.json()
    if not rows:
        return None
    row = rows[0]
    if row["status"] == "claimed":
        return row["claimed_by_user_id"]
    return None


def run_pairing_flow(timeout_seconds: int = 600) -> str | None:
    """Eşleştirmeyi başlatır, tarayıcıyı açar, eşleşene kadar bekler. Başarılı
    olursa user_id'yi config'e yazıp döner; zaman aşımında None döner."""
    import webbrowser

    instance_id = get_or_create_desktop_instance_id(CONFIG_PATH)
    code = request_pairing_code(instance_id)
    webbrowser.open(f"{PAIRING_WEB_URL}?code={code}")

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        user_id = check_pairing_status(code)
        if user_id is not None:
            config = load_config(CONFIG_PATH)
            config["user_id"] = user_id
            save_config(CONFIG_PATH, config)
            return user_id
        time.sleep(POLL_INTERVAL_SECONDS)
    return None


if __name__ == "__main__":
    result = run_pairing_flow()
    if result:
        print(f"Eşleştirme başarılı. user_id: {result}")
    else:
        print("Eşleştirme zaman aşımına uğradı.")
```

- [ ] **Step 5: Testlerin geçtiğini doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_pairing.py -v
```

Expected: 7 test PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ai_notifier/core/pairing.py tests/test_pairing.py pyproject.toml
git commit -m "feat: add pairing code generation, config storage, Supabase REST calls"
```

---

### Task 3: Next.js İskeleti (`web/`)

**Files:**
- Create: `web\package.json`
- Create: `web\tsconfig.json`
- Create: `web\next.config.js`
- Create: `web\.env.local.example`
- Create: `web\.gitignore`
- Create: `web\app\layout.tsx`
- Create: `web\app\page.tsx`
- Create: `web\lib\supabase.ts`

- [ ] **Step 1: `package.json` dosyasını yaz**

```json
{
  "name": "ai-notifier-web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "@supabase/supabase-js": "2.45.4",
    "qrcode": "1.5.4"
  },
  "devDependencies": {
    "typescript": "5.5.4",
    "@types/node": "20.14.15",
    "@types/react": "18.3.3",
    "@types/qrcode": "1.5.5"
  }
}
```

- [ ] **Step 2: `tsconfig.json` dosyasını yaz**

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: `next.config.js` dosyasını yaz**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {};

module.exports = nextConfig;
```

- [ ] **Step 4: `.env.local.example` ve `.gitignore` dosyalarını yaz**

`web\.env.local.example`:
```
NEXT_PUBLIC_SUPABASE_URL=https://wvhlikiiqrculbpvphxk.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

`web\.gitignore`:
```
node_modules/
.next/
.env.local
```

- [ ] **Step 5: `lib/supabase.ts` dosyasını yaz**

```typescript
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

- [ ] **Step 6: `app/layout.tsx` ve `app/page.tsx` dosyalarını yaz**

`web\app\layout.tsx`:
```tsx
export const metadata = {
  title: "AI-Notifier",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
```

`web\app\page.tsx`:
```tsx
export default function HomePage() {
  return <p>AI-Notifier cihaz eşleştirme servisi.</p>;
}
```

- [ ] **Step 7: Bağımlılıkları kur ve gerçek `.env.local` dosyasını oluştur**

```powershell
cd D:\ai-notifier\web
npm install
Copy-Item .env.local.example .env.local
```

`.env.local` içindeki `NEXT_PUBLIC_SUPABASE_ANON_KEY` değerini Supabase Dashboard →
Project Settings → API → "anon public" anahtarıyla değiştir.

- [ ] **Step 8: Build'in başarılı olduğunu doğrula**

```powershell
npm run build
```

Expected: Build hatasız tamamlanır (`✓ Compiled successfully` benzeri bir çıktı).

- [ ] **Step 9: Commit**

```bash
git add web/package.json web/tsconfig.json web/next.config.js web/.env.local.example web/.gitignore web/app web/lib
git commit -m "chore: scaffold Next.js app for device pairing web pages"
```

(`web/.env.local` commit EDİLMEZ — `.gitignore`'da, gerçek anon key'i içeriyor.)

---

### Task 4: `/pair` Sayfası (QR + Realtime)

**Files:**
- Create: `web\app\pair\page.tsx`

**Interfaces:**
- Consumes: `supabase` (Task 3, `lib/supabase.ts`), `qrcode` npm paketi

- [ ] **Step 1: Sayfayı yaz**

```tsx
"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import QRCode from "qrcode";
import { supabase } from "@/lib/supabase";

export default function PairPage() {
  const searchParams = useSearchParams();
  const code = searchParams.get("code") ?? "";
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [claimed, setClaimed] = useState(false);

  useEffect(() => {
    if (!code) return;
    const claimUrl = `${window.location.origin}/pair/claim?code=${code}`;
    QRCode.toDataURL(claimUrl).then(setQrDataUrl);
  }, [code]);

  useEffect(() => {
    if (!code) return;

    const channel = supabase
      .channel(`pairing_codes_${code}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "pairing_codes",
          filter: `code=eq.${code}`,
        },
        (payload) => {
          if ((payload.new as { status: string }).status === "claimed") {
            setClaimed(true);
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [code]);

  if (!code) {
    return <p>Eksik eşleştirme kodu.</p>;
  }

  return (
    <main style={{ fontFamily: "sans-serif", textAlign: "center", padding: "2rem" }}>
      <h1>AI-Notifier Cihaz Eşleştirme</h1>
      {claimed ? (
        <p>✅ Eşleştirildi! Masaüstü uygulamasına dönebilirsiniz.</p>
      ) : (
        <>
          <p>Bu kodu telefonunuzla okutun:</p>
          <h2 style={{ fontSize: "2rem", letterSpacing: "0.3em" }}>{code}</h2>
          {qrDataUrl && (
            <img src={qrDataUrl} alt="Eşleştirme QR kodu" width={240} height={240} />
          )}
          <p>Bekleniyor...</p>
        </>
      )}
    </main>
  );
}
```

- [ ] **Step 2: Build'in hâlâ başarılı olduğunu doğrula**

```powershell
cd D:\ai-notifier\web
npm run build
```

Expected: Hatasız tamamlanır.

- [ ] **Step 3: Yerel sunucuda manuel görsel doğrulama**

```powershell
npm run dev
```

Tarayıcıda `http://localhost:3000/pair?code=TEST01` adresine git. Sayfanın kodu ve
QR görüntüsünü gösterdiğini doğrula (Supabase'de gerçek bir satır olmadığı için
"Bekleniyor..." durumunda kalması normal).

- [ ] **Step 4: Commit**

```bash
git add web/app/pair/page.tsx
git commit -m "feat: add /pair page with QR code and realtime status"
```

---

### Task 5: `/pair/claim` Sayfası (Sihirli Link + Claim)

**Files:**
- Create: `web\app\pair\claim\page.tsx`

**Interfaces:**
- Consumes: `supabase` (Task 3)

- [ ] **Step 1: Sayfayı yaz**

```tsx
"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";

type ClaimResult = "idle" | "success" | "error";

export default function ClaimPage() {
  const searchParams = useSearchParams();
  const code = searchParams.get("code") ?? "";
  const [email, setEmail] = useState("");
  const [linkSent, setLinkSent] = useState(false);
  const [claimResult, setClaimResult] = useState<ClaimResult>("idle");

  useEffect(() => {
    if (!code) return;

    async function claimCode(userId: string) {
      const { error } = await supabase
        .from("pairing_codes")
        .update({ status: "claimed", claimed_by_user_id: userId })
        .eq("code", code)
        .eq("status", "pending");

      if (error) {
        setClaimResult("error");
        return;
      }

      const { data: row } = await supabase
        .from("pairing_codes")
        .select("desktop_instance_id")
        .eq("code", code)
        .single();

      if (row) {
        await supabase.from("devices").insert({
          user_id: userId,
          desktop_instance_id: row.desktop_instance_id,
        });
      }

      setClaimResult("success");
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        claimCode(session.user.id);
      }
    });

    const { data: authListener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        claimCode(session.user.id);
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, [code]);

  async function sendMagicLink(e: React.FormEvent) {
    e.preventDefault();
    await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/pair/claim?code=${code}` },
    });
    setLinkSent(true);
  }

  if (!code) {
    return <p>Eksik eşleştirme kodu.</p>;
  }

  if (claimResult === "success") {
    return <p>✅ Eşleştirme başarılı! Masaüstünüze dönebilirsiniz.</p>;
  }

  if (claimResult === "error") {
    return <p>❌ Kod geçersiz veya süresi dolmuş. Masaüstünde yeni bir kod oluşturun.</p>;
  }

  if (linkSent) {
    return <p>E-postanıza bir giriş linki gönderdik. Linke tıklayın.</p>;
  }

  return (
    <main style={{ fontFamily: "sans-serif", textAlign: "center", padding: "2rem" }}>
      <h1>AI-Notifier ile Eşleştir</h1>
      <form onSubmit={sendMagicLink}>
        <input
          type="email"
          required
          placeholder="E-posta adresiniz"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <button type="submit">Giriş linki gönder</button>
      </form>
    </main>
  );
}
```

- [ ] **Step 2: Build'in başarılı olduğunu doğrula**

```powershell
cd D:\ai-notifier\web
npm run build
```

Expected: Hatasız tamamlanır.

- [ ] **Step 3: Commit**

```bash
git add web/app/pair/claim/page.tsx
git commit -m "feat: add /pair/claim page with magic link auth and claim logic"
```

---

### Task 6: Vercel Deploy + Uçtan Uca Doğrulama

**Files:**
- Modify: `src\ai_notifier\core\pairing.py` (Task 2'deki yer tutucular)

- [ ] **Step 1: Supabase anon key'i al ve `pairing.py`'ı güncelle**

Supabase Dashboard → Project Settings → API → "Project API keys" → "anon public"
değerini kopyala. `src\ai_notifier\core\pairing.py` içinde:

```python
SUPABASE_ANON_KEY = "REPLACE_WITH_YOUR_SUPABASE_ANON_KEY"
```

satırını gerçek değerle güncelle.

- [ ] **Step 2: Vercel projesinin Root Directory'sini ayarla**

Vercel Dashboard → `ai-notifier` projesi → Settings → General → "Root Directory" →
`web` yaz → Save. Bu, Vercel'in repo kökündeki Python kodunu değil, `web/` klasöründeki
Next.js uygulamasını deploy etmesini sağlar (önceki "No python entrypoint found" hatasının
kök nedeni buydu).

- [ ] **Step 3: Vercel'e ortam değişkenlerini ekle**

Vercel Dashboard → Settings → Environment Variables → ekle:
- `NEXT_PUBLIC_SUPABASE_URL` = `https://wvhlikiiqrculbpvphxk.supabase.co`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` = (Step 1'deki anon key)

- [ ] **Step 4: Yeniden deploy et ve Vercel URL'sini al**

Vercel Dashboard → Deployments → "Redeploy" (veya yeni bir commit push'la). Deploy
başarılı olduğunda atanan domain'i not al (örn. `https://ai-notifier-tau.vercel.app`).

- [ ] **Step 5: `pairing.py`'daki `PAIRING_WEB_URL`'i güncelle**

```python
PAIRING_WEB_URL = "REPLACE_WITH_YOUR_VERCEL_URL/pair"
```

satırını gerçek Vercel domain'iyle güncelle (örn.
`"https://ai-notifier-tau.vercel.app/pair"`).

- [ ] **Step 6: Tüm test paketini çalıştır**

```powershell
cd D:\ai-notifier
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: Tüm testler PASS.

- [ ] **Step 7: Uçtan uca manuel senaryo testi**

```powershell
.venv\Scripts\python.exe -m ai_notifier.core.pairing
```

Tarayıcı otomatik açılıp kodu göstermeli. Telefonunla QR'ı tara (veya `/pair/claim?code=...`
adresini elle aç), e-posta adresini gir, gelen linke tıkla. `/pair` sayfasının
"Eşleştirildi!" gösterdiğini ve terminalin `Eşleştirme başarılı. user_id: ...` yazdığını
doğrula.

- [ ] **Step 8: Commit**

```bash
git add src/ai_notifier/core/pairing.py
git commit -m "feat: wire real Supabase/Vercel values into pairing flow"
```

---

## Self-Review Notları

- **Spec kapsaması:** Eşleştirme akışı (Task 2, 4, 5, 6), veri modeli/RLS (Task 1),
  hata yönetimi (spec bölüm 5: kod bulunamazsa `check_pairing_status` None döner, Task 5'te
  claim hatası UI'da gösterilir) — spec'in 2-5. bölümleri kapsandı.
- **Placeholder taraması:** `SUPABASE_ANON_KEY` ve `PAIRING_WEB_URL` yer tutucuları
  Task 6'da nasıl doldurulacağı net şekilde işaretli (gerçek kurulum zamanı değerleri).
- **Tip tutarlılığı:** `check_pairing_status` her yerde `str | None` (user_id veya None)
  döner; `run_pairing_flow` da aynı tipi döner. Next.js tarafında `claimed_by_user_id`
  alan adı Python tarafındaki JSON anahtarıyla (Supabase kolon adı) tutarlı.
