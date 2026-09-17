# AI-Notifier — Tasarım: Mobil Eşlikçi Uygulama / Push Bildirimi (Faz 2, Alt-Proje 3/3)

**Tarih:** 2026-09-17
**Mimar/Geliştirici:** Selman
**Durum:** Onaylandı (brainstorming aşaması tamamlandı)
**Kaynak:** `AIPing_Proje_Plani.pdf` Faz 2; [2026-09-17-device-pairing-design.md](2026-09-17-device-pairing-design.md)

## 1. Amaç ve Kapsam

Faz 2'nin son alt-projesi: masaüstü servisinin, eşleştirilmiş telefona gerçek Firebase
Cloud Messaging (FCM) push bildirimi gönderebilmesi. Kapsam sadece bu — genel bir mobil
uygulama deneyimi (sohbet geçmişi görüntüleme, ayarlar vb.) DEĞİL.

**Kapsam dışı:** "Kullanıcı bilgisayar başında mı" tespiti (boşta kalma algılama) —
brainstorming kararı: masaüstü bildirimi her zaman push ile birlikte gönderilir, YAGNI.

**Platform:** Sadece Android (Selman'ın cihazı). iOS kapsam dışı.

**Yeni dış bağımlılıklar (Selman'ın kendi yapması gereken kurulumlar):**
- Yeni bir Firebase projesi (Supabase'den ayrı) — Cloud Messaging açık, bir Android
  uygulaması eklenmiş, `google-services.json` indirilmiş.
- Firebase Admin SDK için bir servis hesabı JSON anahtarı (masaüstü tarafında push
  göndermek için).
- Expo "development build" (Expo Go YETMEZ — gerçek Firebase SDK'sı native kod
  gerektiriyor, `expo prebuild`/EAS build ile kurulmalı).

## 2. Güvenlik: FCM Token Okuma

Masaüstü, hangi telefona push göndereceğini bilmek için `devices` tablosundaki
`fcm_token`'ı okumalı. Ama masaüstü hiçbir Supabase kullanıcı oturumuna sahip değil
(sadece bir `user_id` string'i biliyor) — bu yüzden düz bir anon SELECT ilkesi,
**herkese açık anon anahtarla tüm kullanıcıların FCM token'larının dökülmesine** izin
verirdi (GitHub'da public olan anon key ile kimse `devices` tablosunu filtresiz
sorgulayabilir).

**Çözüm:** Dar kapsamlı bir Postgres RPC fonksiyonu (`security definer`):
masaüstü sadece kendi `desktop_instance_id`'siyle (rastgele, tahmin edilemez bir UUID)
çağırır, fonksiyon SADECE o satırın `fcm_token`'ını döner — başka hiçbir satır
görünmez/listelenemez. Bu, `pairing_codes` tablosundaki mevcut güvenlik yaklaşımıyla
tutarlı (bilinmesi zor bir değerle dar kapsamlı erişim).

## 3. Veri Modeli Değişikliği

`devices` tablosuna:
```sql
alter table devices add column if not exists fcm_token text;
```

Yeni RLS ilkesi (authenticated, yani mobil app girişi yapmış kullanıcı, kendi cihaz
kaydını güncelleyebilir):
```sql
create policy "authenticated can update own device fcm token"
  on devices for update
  to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());
```

Yeni RPC fonksiyonu:
```sql
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

## 4. Bileşenler

### 4.1 Mobil Uygulama (`mobile/` — yeni Expo projesi)
- Tek ekran: e-posta ile sihirli link girişi (web'deki `/pair/claim` ile aynı yöntem,
  ayrı bir Supabase Auth oturumu — mobil app'in kendi giriş akışı).
- Giriş sonrası: `@react-native-firebase/messaging` ile FCM token alınır, giriş yapan
  kullanıcının `devices` satır(lar)ına yazılır (`.eq('user_id', ...)` ile RLS zaten
  sadece kendi satırına izin veriyor).
- Custom URL scheme (`ainotifier://`) ile sihirli link e-postası doğrudan uygulamaya
  dönebilsin diye Supabase Auth redirect URL listesine eklenir.

### 4.2 Masaüstü (`src/ai_notifier/notifications/push.py` — yeni)
- `PushNotifier(NotificationSender)`: `send(title, message)` çağrıldığında, yerel
  config'teki `desktop_instance_id`'yi kullanarak RPC ile fcm_token'ı sorgular; token
  yoksa (henüz eşleşme yok veya telefon hiç giriş yapmadı) sessizce hiçbir şey yapmaz.
  Token varsa Firebase Admin SDK (`firebase_admin.messaging.send`) ile push gönderir.
- `core/dispatcher.py`: `NotificationDispatcher` artık tek bir `notifier` yerine bir
  `notifiers: list[NotificationSender]` alır, her onaylanan durum değişikliğinde
  LİSTEDEKİ HEPSİNE gönderir (Windows Toast + Push birlikte, brainstorming kararı).

## 5. Hata Yönetimi

- FCM token bulunamazsa (`get_fcm_token_for_desktop` boş/None döner): `PushNotifier`
  sessizce hiçbir şey yapmaz, hata fırlatmaz (masaüstü bildirimi zaten gönderilmiş olur).
- Firebase Admin SDK çağrısı hata verirse (geçersiz token, ağ hatası): loglanır, servis
  çökmez — masaüstü bildirim akışını etkilemez.

## 6. Test Stratejisi

- `get_fcm_token_for_desktop` çağrısını yapan Python fonksiyonu, mevcut
  `request_pairing_code`/`check_pairing_status` desenine uygun şekilde enjekte edilebilir
  bir `http_post` ile birim testiyle kapsanır.
- `PushNotifier.send`, sahte (fake) bir Firebase gönderme fonksiyonu enjekte edilerek
  test edilir (gerçek Firebase'e bağımlı olmadan).
- Mobil uygulama ve gerçek Firebase entegrasyonu, Selman'ın kendi Android cihazında
  manuel senaryo testiyle doğrulanır (bu projedeki tüm OS/donanım-seviyesi
  entegrasyonlarda izlenen desen).

## 7. Açık Riskler

- Firebase projesi kurulumu tamamen Selman'a bağımlı — implementasyon planı bu adımları
  ayrı, net bir kurulum görevine ayırmalı.
- Expo development build kurulumu (Expo Go yerine) ilk kez yapılıyor, beklenenden fazla
  sürebilir (Android SDK/Gradle gereksinimleri gibi).
- `devices` tablosunda kullanıcı başına birden fazla satır varsa (çoklu masaüstü),
  mobil app'in FCM token güncellemesi TÜM satırları güncelleyecek şekilde
  tasarlanmıştır (MVP basitleştirmesi, YAGNI).
