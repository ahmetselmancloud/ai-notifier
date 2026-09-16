# AI-Notifier (PingAI) — MVP Tasarımı: Windows Masaüstü Sensörü

**Tarih:** 2026-09-16
**Mimar/Geliştirici:** Selman
**Durum:** Onaylandı (brainstorming aşaması tamamlandı)
**Kaynak:** `AIPing_Proje_Plani.pdf` (Eylül 2026 master plan)

## 1. Amaç ve Kapsam

Bu spec, PDF'deki master planın **Faz 0 (teknik doğrulama) + Faz 1 (MVP)** bölümünü kapsar:
YZ sohbet uygulamalarının (başlangıçta Claude Desktop ve ChatGPT Desktop) durumunu Windows
üzerinde arka planda izleyip, yanıt tamamlandığında / onay beklediğinde / hata oluştuğunda
Windows Toast bildirimi gönderen bir masaüstü servisi.

**Kapsam dışı (sonraki spec'lere bırakılıyor):** Tarayıcı eklentisi, mobil eşlikçi uygulama (FCM),
Donanım Sensörü (Ollama/LM Studio GPU-CPU takibi), Mac desteği, Next.js/Supabase auth altyapısı.
Mimari bu genişlemelere hazır şekilde kurulacak ama MVP bunları içermeyecek.

**Proje hedefi:** Baştan açık kaynak/ürün olarak konumlandırılıyor (Microsoft Store, Product Hunt
lansmanı nihai hedef) — bu yüzden MVP kodu da başkalarının kurup çalıştırabileceği, okunabilir
bir yapıda olmalı.

## 2. Faz 0 — Teknik Doğrulama (spike, ilk yapılacak iş)

Brainstorming sırasında Claude Code penceresi üzerinde yapılan hızlı bir UIAutomation denemesi
önemli bir bulgu ortaya çıkardı: **ilk okuma çoğu zaman boş/tutarsız döner, ikinci/üçüncü
denemede içerik elemanları (buton, mesaj alanı, "Stop" butonu vb.) görünür hale gelir.**
Bu, Electron tabanlı uygulamaların UI ağacını her zaman anında ve güvenilir şekilde
göstermediğini kanıtlıyor — plan bu riski MVP başlamadan önce doğrulamalı.

Faz 0'ın çıktısı: Claude Desktop ve ChatGPT Desktop'a karşı çalıştırılan, aşağıdakileri
doğrulayan küçük bir Python doğrulama betiği (proje kodunun parçası, ama ürün özelliği değil):

- Her iki uygulamada da "üretim devam ediyor" (örn. Stop butonu) ve "onay/seçenek bekliyor"
  (örn. "Devam Et", "İzin Ver" butonları) durumları UIAutomation ile ayırt edilebiliyor mu?
- Pencere **minimize edilmişken veya arka sekmedeyken** de aynı okuma çalışıyor mu? (Bu,
  kullanıcının açıkça belirttiği bir zorunlu gereksinim.)
- Kaç deneme/retry ile okuma kararlı hale geliyor?

Faz 0 başarısız olursa (örn. bir uygulamada UIAutomation hiç güvenilir sinyal vermiyorsa),
o uygulama için Yaklaşım A yerine sonraki bir spec'te ele alınacak bir fallback tartışılır —
MVP mimarisine dokunulmaz, sadece o adaptörün iç mantığı değişir.

## 3. Mimari

### 3.1 Bileşenler

- **Core ("Brain"):** Python, sistem tepsisinde (system tray) arka planda çalışan servis.
  `asyncio` event loop üzerinde adaptörleri yönetir.
- **Sensör adaptörleri:** Her YZ uygulaması için ortak bir arayüzü (`BaseSensor`) uygulayan
  ayrı bir sınıf. MVP'de iki somut adaptör: `ClaudeDesktopSensor`, `ChatGPTDesktopSensor`.
  Bu arayüz sayesinde ileride web/Ollama/Open WebUI/Mac desteği eklemek, core'a dokunmadan
  yeni bir adaptör sınıfı yazmak anlamına gelir.
- **Bildirim katmanı:** MVP'de sadece Windows Toast Notification. Arayüz soyutlanır ki
  Faz 2'de FCM push aynı katmana eklenebilsin.

### 3.2 Tespit Mekanizması (Yaklaşım A: Çoklu-sinyal UIAutomation)

Ekran görüntüsü/OCR tabanlı yaklaşımlar (B, C) elenmiştir çünkü kullanıcının zorunlu
gereksinimiyle (pencere minimize/arka plandayken de çalışmalı) uyumsuzdur — OCR, ekranda
görünmeyen bir pencerenin pikselini yakalayamaz. UIAutomation API'si ise pencere görünür
olmasa bile UI ağacını okuyabilir.

Her adaptör:

1. **Event subscription (olay aboneliği), polling değil.** Windows UI Automation'ın
   `AutomationEventHandler` mekanizmasıyla ilgili pencerenin yapı/özellik değişikliklerine
   abone olunur. Servis çoğu zaman "uyur", yalnızca gerçek bir UI değişikliği olduğunda
   Windows tarafından tetiklenir. Bu, sabit aralıklı polling'e (örn. her 2 sn'de bir tüm
   ağacı taramak) kıyasla CPU/pil yükünü neredeyse sıfıra indirir.
2. **Hedefe kilitli sorgu.** Tetiklendiğinde adaptör tüm pencere ağacını değil, sadece
   ilgili window handle içinde beklenen control type/name desenlerini arar (tam ağaç
   dump'ı yapmaz).
3. **Kararlılık doğrulama (debounce).** Faz 0'da gözlenen flaky-read sorununa karşı, bir
   durum değişikliği yalnızca art arda N okuma aynı sonucu verdiğinde kesinleşir ve
   bildirime dönüşür.
4. **Durum çıktısı:** `GENERATING`, `DONE`, `WAITING_APPROVAL`, `ERROR`, `UNKNOWN`.
   `UNKNOWN` durumunda (uygulama kapalı, sinyal okunamıyor) sessizce beklenir, bildirim
   gönderilmez — yanlış pozitiften kaçınmak önceliklidir.

### 3.3 Veri Akışı

```
Windows UI Automation event → Adaptör (hedefe kilitli okuma + retry) →
Debounce/kararlılık kontrolü → Core karar motoru → Bildirim katmanı → Windows Toast
```

### 3.4 Hata Yönetimi

- Hedef uygulama kapalı/bulunamıyor → adaptör `UNKNOWN` döner, sessizce bekler.
- UIAutomation COM çağrısı exception fırlatırsa → yakalanıp loglanır, adaptör bir sonraki
  event'te tekrar dener; servis çökmez.

## 4. Performans Beklentisi

- **CPU:** Event-driven olduğu için ortalama %1'in altında; yalnızca gerçek bir durum
  değişikliğinde kısa bir işlem sıçraması.
- **RAM:** ~40-80 MB (Python + `uiautomation`/`comtypes` kütüphaneleri).
- **Pil etkisi:** Polling'e kıyasla ihmal edilebilir düzeyde.
- OCR/vision kullanılmadığı için GPU'ya hiç dokunulmaz.

## 5. Test Stratejisi

UIAutomation'ı mock'lamanın gerçek değeri düşük (asıl risk gerçek uygulamaların davranışı).
Bu yüzden:

- Faz 0 doğrulama betiği, gerçek Claude Desktop / ChatGPT Desktop'a karşı manuel senaryo
  testleri olarak kalır (generating / waiting-approval / error durumlarını elle tetikleyip
  doğru bildirim geldiğini doğrulama).
- Core karar motoru (debounce, state machine) saf Python mantığı olduğu için normal birim
  testleriyle kapsanır.

## 6. Teknoloji Yığını (MVP için)

| Bileşen | Teknoloji |
|---|---|
| Core servis | Python 3.x, `asyncio` |
| UI okuma | `uiautomation` (Windows UI Automation sarmalayıcısı) |
| Bildirim | Windows Toast (`winrt`/`win10toast` benzeri) |
| Paketleme (Faz 3'e hazırlık, MVP'de değil) | PyInstaller |

## 7. Proje Konumu

`D:\ai-notifier` — yeni, bağımsız git deposu. restoran-qr ve diğer işlerden ayrı.

## 8. Açık Riskler

- Faz 0 sonucu Claude Desktop/ChatGPT Desktop'ta UIAutomation sinyalleri yetersiz çıkarsa,
  bu spec'in 3.2 bölümü revize edilmeli.
- Uygulama güncellemeleri (Claude Desktop/ChatGPT Desktop yeni sürüm) UI yapısını
  değiştirirse adaptörler kırılabilir — bu, uzun vadeli bakım riski olarak kabul edilmiştir
  (PDF'in kendisinin de işaret ettiği bir gerçek).
