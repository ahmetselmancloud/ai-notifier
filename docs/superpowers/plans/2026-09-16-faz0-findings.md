# Faz 0 Bulguları

**Test edilen ortam:** Claude penceresi (Chrome_WidgetWin_1 / Electron), Handle 1049628.
ChatGPT Desktop bu geliştirme ortamında kurulu değil, test edilemedi.

## Bulgu 1: İçerik alanı `uiautomation` paketiyle okunamıyor

`scripts/spike_uiautomation_probe.py` ile 5 art arda denemede (1 sn arayla), pencerenin
içerik alanında (mesajlar, "Stop" butonu vb.) **hiçbir eleman bulunamadı** — yalnızca
pencere çerçevesi butonları (Küçült/Büyüt/Geri yükle/Kapat) okunabiliyor.

Bu, brainstorming aşamasında Windows-MCP'nin bir denemesinde aynı pencerede zengin
içerik (Stop butonu, kaydırılabilir mesaj alanı) bulunmasıyla çelişiyor. Aynı pencere
handle'ı (1049628) doğrulandı — farklı bir pencereye bakmıyoruz.

En olası açıklama: Chromium/Electron tabanlı uygulamalar, erişilebilirlik ağacını
varsayılan olarak *tembel* (lazy) oluşturur; yalnızca belirli bir erişilebilirlik
istemcisi (screen reader, belirli COM API çağrıları) tetiklediğinde tam ağacı inşa
eder. Python `uiautomation` paketinin basit `GetChildren()` taraması bu tetiklemeyi
yapmıyor olabilir.

## Bulgu 2: `uiautomation` paketinde olay aboneliği (event subscription) API'si yok

Spec'in 3.2 bölümünde ve implementasyon planının Task 7/8'inde varsayılan
`auto.AddAutomationEventHandler(...)` fonksiyonu, kurulu `uiautomation==2.0.29`
paketinde **mevcut değil** (`AttributeError: module 'uiautomation' has no attribute
'AddAutomationEventHandler'`). Paket kaynağında hiçbir olay/event API'si yok.

Bu, spec'in "polling değil, event subscription" mimari kararının seçilen kütüphaneyle
şu haliyle **uygulanamaz** olduğu anlamına geliyor.

## Sonuç

Faz 0'ın amacı tam da bunu ortaya çıkarmaktı: MVP mimarisinin iki temel varsayımı
(güvenilir içerik okuma + event-driven tespit), seçilen kütüphaneyle doğrulanmadı.
Bu, spec'in 3.2 bölümünün ve implementasyon planının Task 7-9'unun gözden geçirilmesini
gerektiriyor. Devam etmeden önce kullanıcıyla (Selman) seçenekler tartışıldı.
