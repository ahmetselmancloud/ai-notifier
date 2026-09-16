# AI-Notifier — Tasarım: Tarayıcı Eklentisi (Faz 2, Alt-Proje 1/3)

**Tarih:** 2026-09-17
**Mimar/Geliştirici:** Selman
**Durum:** Onaylandı (brainstorming aşaması tamamlandı)
**Kaynak:** `AIPing_Proje_Plani.pdf` Faz 2; [2026-09-16-mvp-windows-desktop-sensor-design.md](2026-09-16-mvp-windows-desktop-sensor-design.md)

## 1. Amaç ve Kapsam

PDF'in Faz 2'si üç bağımsız alt-projeyi birden tanımlıyor: tarayıcı eklentisi, cihaz
eşleştirme/auth (Next.js + Supabase), mobil eşlikçi uygulama (FCM). Bunlar tek spec'te
tasarlanamayacak kadar bağımsız; bu spec **sadece 1. alt-projeyi** kapsar:

> Chrome/Edge (Manifest V3) tarayıcı eklentisi, claude.ai ve chatgpt.com sekmelerini
> MutationObserver ile izler, durum değişikliklerini yerel bir WebSocket bağlantısı
> üzerinden [Windows masaüstü servisine](2026-09-16-mvp-windows-desktop-sensor-design.md)
> iletir. Servis, bu bilgiyi mevcut `DecisionEngine`/bildirim katmanından geçirir.

**Kapsam dışı (sonraki alt-projeler):** Cihaz eşleştirme/auth (Next.js+Supabase), mobil
FCM alıcısı. Sıralama: 1) bu spec → 2) auth/eşleştirme → 3) mobil app.

## 2. Faz 0 — DOM Doğrulaması (tamamlandı)

Gerçek, oturum açık bir claude.ai sekmesinde (Selman'ın kendi Chrome'u, Claude in Chrome
aracıyla) canlı bir mesaj gönderilip DOM incelendi. Bulgular:

- **`[data-testid="chat-input-stop"]`**, `aria-label="Stop response"` — yanıt üretilirken
  DOM'da mevcut, tamamlanınca DOM'dan tamamen kaldırılıyor (sadece gizlenmiyor). Dile/metne
  bağlı olmayan, kararlı bir sinyal.
- **Yanlış varsayım düzeltildi:** `[data-testid="action-bar-retry"]` her tamamlanmış
  mesajda normalde mevcut bir aksiyon butonu — hata göstergesi DEĞİL. İlk tasarımda "Retry"
  metnini hata sinyali sayma planı hatalıydı, çıkarıldı.
- **Doğrulanamadı (açık risk):** Onay/araç izni isteyen ("Devam Et", "İzin Ver" tarzı)
  butonların ve hata banner'larının gerçek `data-testid`/yapısı — bu oturumda böyle bir
  senaryo tetiklenemedi. ChatGPT Desktop adaptöründeki gibi, bu ikisi ilk implementasyonda
  **tahmini** kalacak, gerçek kullanımda düzeltilecek.
- chatgpt.com için hiç DOM incelemesi yapılmadı (Selman'da ChatGPT hesabı/kurulumu yok) —
  aynı tahmini durum masaüstü ChatGPT adaptöründe olduğu gibi geçerli.

## 3. Mimari

### 3.1 Bileşenler

- **Content script** (`extension/content_script.js`): Her hedef sitede (claude.ai,
  chatgpt.com) çalışır. Sohbet konteynerinde `MutationObserver` ile
  `[data-testid="chat-input-stop"]` elemanının eklenip/çıkarılmasını izler. Durum
  değişikliğini `chrome.runtime.sendMessage` ile background script'e iletir.
- **Background service worker** (`extension/background.js`): Content script'lerden gelen
  mesajları alır, yerel WebSocket bağlantısını (bkz. 3.2) yönetir, bağlantı koptuğunda
  yeniden bağlanır.
- **Web bridge** (`src/ai_notifier/core/web_bridge.py`): Masaüstü servisinin aynı asyncio
  döngüsünde çalışan yerel HTTP+WebSocket sunucusu (`127.0.0.1:8765`). Token üretir/doğrular,
  gelen `{site, state}` mesajlarını `DecisionEngine.submit_reading()`'e iletir.

### 3.2 Güvenlik: Yerel Token Dağıtımı

Content script'ler dosya sistemini okuyamaz; bu yüzden [masaüstü sensör
spec'inin](2026-09-16-mvp-windows-desktop-sensor-design.md) genel "yerel güvenlik"
kararı şöyle uygulanır:

1. Servis başlarken rastgele bir token üretir (bellekte tutulur, diske yazılmaz).
2. `GET http://127.0.0.1:8765/token` endpoint'i bu token'ı döner, yanıt başlığında
   `Access-Control-Allow-Origin: chrome-extension://<EKLENTI_ID>` bulunur — bu sayede
   **sadece bizim eklentimiz** (bilinen ID'siyle) tarayıcının CORS mekanizmasıyla yanıtı
   okuyabilir; rastgele bir web sitesinin aynı isteği yapması teknik olarak mümkün ama
   yanıtı okuyamaz.
3. Background script, WebSocket bağlantısının ilk mesajında bu token'ı gönderir.
   Sunucu, token doğrulanana kadar başka hiçbir mesajı işlemez; geçersiz/eksik token'lı
   bağlantıyı kapatır.

### 3.3 Veri Akışı

```
Sayfa DOM değişikliği → MutationObserver (content script) →
chrome.runtime.sendMessage → background script → WebSocket (tokenlı) →
web_bridge.py → DecisionEngine.submit_reading("Claude (Web)"/"ChatGPT (Web)", state) →
(mevcut) mesaj eşleme → bildirim katmanı
```

`DecisionEngine` ve bildirim katmanı [masaüstü MVP'sinde](2026-09-16-mvp-windows-desktop-sensor-design.md)
zaten var ve değişmeden yeniden kullanılıyor — web bridge sadece yeni bir "sensör kaynağı".

### 3.4 Hata Yönetimi

- WebSocket bağlantısı koparsa (servis kapalı/yeniden başlıyor), background script
  üstel geri çekilmeyle (exponential backoff, max ~30 sn) yeniden bağlanmayı dener.
- Content script, sayfa henüz tam yüklenmeden `MutationObserver` hedefini bulamazsa,
  hedef konteyner DOM'a eklenene kadar `document.body` üzerinde geçici bir gözlemci
  ile bekler.
- Token doğrulaması başarısız olan bağlantılar sessizce kapatılır, sunucu loglar
  (uyarı seviyesinde), servis çökmez.

## 4. Dosya Yapısı

```
D:\ai-notifier\
  extension\
    manifest.json
    content_script.js
    background.js
  src\ai_notifier\core\
    web_bridge.py        # HTTP token endpoint + WebSocket sunucu
    service.py            # (değişecek) web_bridge'i aynı asyncio loop'ta başlatır
```

## 5. Test Stratejisi

- `web_bridge.py`'nin token üretimi/doğrulama mantığı saf Python — birim testleriyle
  kapsanır (gerçek WebSocket olmadan, mesaj işleme fonksiyonu ayrıştırılıp test edilir).
- Content script'in MutationObserver mantığı, gerçek bir tarayıcıda (Claude in Chrome
  aracıyla) claude.ai'da manuel senaryo testiyle doğrulanır — masaüstü sensörlerindeki
  gibi otomatik test yazmanın gerçek değeri düşük.

## 6. Açık Riskler

- Onay/hata sinyalleri (bkz. Bölüm 2) doğrulanmadı — gerçek bir tool-use onay senaryosu
  tetiklenip DOM incelenmeli.
- chatgpt.com hiç incelenmedi, tüm selektörler tahmini.
- MV3 service worker'lar ~30 sn hareketsizlikte durdurulabilir; aktif bir WebSocket
  bağlantısının bunu engellediği biliniyor ama gerçek kullanımda (sekme uzun süre arka
  planda kalırsa) doğrulanmalı.
