# AI-Notifier — Tasarım: Cihaz Eşleştirme / Auth (Faz 2, Alt-Proje 2/3)

**Tarih:** 2026-09-17
**Mimar/Geliştirici:** Selman
**Durum:** Onaylandı (brainstorming aşaması tamamlandı)
**Kaynak:** `AIPing_Proje_Plani.pdf` Faz 2; [2026-09-17-browser-extension-design.md](2026-09-17-browser-extension-design.md)

## 1. Amaç ve Kapsam

Bu spec, Faz 2'nin 2. alt-projesini kapsar: masaüstü servisinin ve (henüz yapılmamış)
mobil eşlikçi uygulamanın **aynı hesaba** bağlanabilmesi için minimal bir eşleştirme/auth
sistemi. Tek amacı bu — genel bir hesap/dashboard sistemi DEĞİL.

**Neden gerekli:** Masaüstü servisi, kullanıcı bilgisayar başında olmadığında mobil
cihaza push bildirimi göndermek isteyecek (Faz 2 alt-proje 3). Ama masaüstü ve mobil
farklı cihazlar — masaüstünün "hangi telefona göndereceğini" bilmesi için ikisinin
ortak, internet üzerinden erişilebilen bir kayıtta (Supabase) eşleştirilmiş olması
gerekiyor.

**Kapsam dışı:** Mobil uygulamanın kendisi (Faz 2 alt-proje 3, FCM token kaydı dahil),
genel kullanıcı hesap/dashboard özellikleri, tarayıcı eklentisi (alt-proje 1, zaten
tamamlandı).

**Altyapı:** Yeni, bağımsız bir Supabase projesi (Selman'ın kendi seçtiği, restoran-qr'dan
ayrı bir hesapta) + Next.js web sitesi (Vercel, `*.vercel.app` ile başlar). Bu kurulumları
Selman kendisi yapar (hesap oluşturma/OAuth Claude tarafından yapılamaz).

## 2. Eşleştirme Akışı

1. Masaüstü servisi ilk çalıştığında kalıcı bir `desktop_instance_id` üretir, yerel bir
   config dosyasında saklar (`%APPDATA%\ai-notifier\config.json`).
2. Kullanıcı bir eşleştirme komutu tetikler (MVP'de basit bir CLI komutu, örn.
   `python -m ai_notifier.core.pairing`).
3. Servis, Supabase'e `pairing_codes` tablosuna `status='pending'` bir satır ekler
   (6 haneli rastgele kod + `desktop_instance_id`, 10 dakika geçerlilik).
4. Servis, varsayılan tarayıcıyı `https://<next-app>/pair?code=XXXXXX` adresine açar.
   Bu sayfa kodu ve bir QR kod (mobil `claim` linkini kodlayan) gösterir.
5. Kullanıcı telefonuyla QR'ı tarar → `https://<next-app>/pair/claim?code=XXXXXX` açılır.
6. Giriş yapılmamışsa e-posta adresi istenir, Supabase Auth sihirli link e-postası
   gönderir. Linke tıklanınca kullanıcı giriş yapmış olur ve otomatik olarak claim
   işlemi tetiklenir: `pairing_codes` satırı `status='claimed'`,
   `claimed_by_user_id=<auth.uid()>` olarak güncellenir; `devices` tablosuna bir satır
   eklenir (`user_id`, `desktop_instance_id`, `paired_at`).
7. `/pair` sayfası (adım 4) Supabase Realtime ile satırı dinler, `claimed` olduğunda
   "Eşleştirildi!" gösterir.
8. Masaüstü servisi aynı zamanda arka planda polling ile (her 2 sn) kodun durumunu
   sorar; `claimed` görünce `claimed_by_user_id`'yi yerel config dosyasına yazar ve
   çıkar.

## 3. Veri Modeli (Supabase)

### `pairing_codes`
| Sütun | Tip | Not |
|---|---|---|
| `code` | text, PK | 6 haneli, örn. `A3F9K2` |
| `desktop_instance_id` | text | Masaüstünün kalıcı kimliği |
| `status` | text | `pending` \| `claimed` |
| `claimed_by_user_id` | uuid, nullable | `auth.users.id` referansı |
| `created_at` | timestamptz | |
| `expires_at` | timestamptz | `created_at + 10 dakika` |

### `devices`
| Sütun | Tip | Not |
|---|---|---|
| `id` | uuid, PK | |
| `user_id` | uuid | `auth.users.id` referansı |
| `desktop_instance_id` | text | |
| `paired_at` | timestamptz | |

### RLS (Row Level Security) İlkeleri
- `pairing_codes`: anon rolü SADECE `status='pending'` bir satır INSERT edebilir
  (kendi oluşturduğu kodu okuyabilmesi için `code` ile eşleşen tek satırı SELECT
  edebilir — pratik bir MVP basitleştirmesi, tüm tabloyu taramaz). Kimliği doğrulanmış
  (authenticated) kullanıcı, SADECE `status='pending'` olan bir satırı `claimed`'a
  güncelleyebilir ve kendi `user_id`'sini yazabilir.
- `devices`: yalnızca authenticated kullanıcı kendi `user_id`'siyle satır ekleyebilir/okuyabilir.

## 4. Bileşenler

### 4.1 Next.js (`web/` — yeni klasör, Vercel'e deploy edilir)
- `/pair` sayfası: kod + QR gösterir, Supabase Realtime ile durumu dinler.
- `/pair/claim` sayfası: e-posta girişi (sihirli link) + otomatik claim mantığı.
- Supabase istemci kütüphanesi (`@supabase/supabase-js`) ile hem `/pair` (anon,
  realtime dinleme) hem `/pair/claim` (authenticated, güncelleme) işlemleri yapılır.

### 4.2 Masaüstü (`src/ai_notifier/core/pairing.py` — yeni)
- `desktop_instance_id` üretimi/yerel saklama.
- Supabase REST API'sine (anon key ile) `pairing_codes` INSERT/SELECT çağrıları.
- Tarayıcı açma (`webbrowser.open`).
- Polling ile eşleşme bekleme, sonucu config dosyasına yazma.

## 5. Hata Yönetimi

- Kod süresi dolarsa (`expires_at` geçmiş), masaüstü polling'i durdurup kullanıcıya
  "Kod süresi doldu, tekrar deneyin" mesajı verir.
- Supabase'e ağ hatası olursa (internet yok), masaüstü polling'i kısa bir backoff ile
  tekrar dener, sürekli hata durumunda kullanıcıya bilgi verip çıkar.
- `/pair/claim` sayfasında geçersiz/süresi dolmuş kod girilirse net bir hata mesajı
  gösterilir.

## 6. Test Stratejisi

- Masaüstü tarafındaki `desktop_instance_id` üretimi/saklama mantığı saf Python,
  birim testiyle kapsanır.
- Supabase REST çağrılarını yapan fonksiyonlar, gerçek bir HTTP istemcisi enjekte
  edilerek (fake/mock) test edilir — gerçek Supabase'e bağımlı olmadan.
- Next.js sayfaları ve gerçek Supabase entegrasyonu (RLS dahil), gerçek bir tarayıcıda
  (Claude in Chrome veya Selman'ın kendi telefonu) manuel senaryo testiyle doğrulanır —
  bu oturumda kullanılan Faz 0 doğrulama desenine benzer.

## 7. Açık Riskler

- Bu spec, Selman'ın kendi Supabase/Vercel hesabında gerçek bir proje oluşturmasına
  bağımlı — implementasyon planı bu kurulum adımlarını (env değişkenleri, proje URL'si)
  açıkça bir kurulum görevine ayırmalı.
- RLS ilkelerinin tam SQL'i implementasyon sırasında yazılıp gerçek Supabase'e karşı
  test edilmeli; buradaki tanımlar mantıksal niyet, kesin syntax değil.
- Mobil uygulama (alt-proje 3) henüz yok — bu spec'in "başarı" ölçütü, `/pair/claim`
  sayfasının bir telefon TARAYICISINDA çalışması; gerçek mobil app'in aynı akışı
  kullanıp kullanmayacağı alt-proje 3'te netleşecek.
