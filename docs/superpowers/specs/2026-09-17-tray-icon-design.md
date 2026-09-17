# AI-Notifier — Tasarım: Sistem Tepsisi İkonu

**Tarih:** 2026-09-17
**Durum:** Onaylandı

## Amaç

Servis çalışırken hiçbir görsel gösterge yok — kullanıcı servisin çalışıp çalışmadığını
anlayamıyor (Selman'ın kendi gözlemi). Basit bir sistem tepsisi ikonu ekleniyor.

## Tasarım

- **Kütüphane:** `pystray` (+ `Pillow`, ikon görüntüsü için).
- **`src/ai_notifier/core/tray.py`:**
  - `create_icon_image() -> PIL.Image.Image` — basit, tek renkli bir ikon üretir
    (gerçek bir logo yok henüz; bu, ileride kolayca değiştirilebilir bir yer tutucu).
  - `build_tray_icon(on_pair, on_quit) -> pystray.Icon` — menü: **"Cihaz Eşleştir"**
    (`on_pair` çağırır) ve **"Çıkış"** (`on_quit` çağırır).
- **`service.py` entegrasyonu:** asyncio döngüsü arka plan (daemon) thread'inde çalışır;
  `icon.run()` ana thread'de çalışır (Windows'ta tepsi ikonları için gerekli). "Çıkış"
  seçilince `icon.stop()` çağrılır ve süreç sonlanır.
- **"Cihaz Eşleştir"** menü öğesi, `pairing.run_pairing_flow()`'u pystray'in kendi
  callback thread'inde çalıştırır (bloklaması sorun değil, tepsi ikonunu dondurmaz).

## Test Stratejisi

- `create_icon_image()` saf/deterministik — birim testiyle (boyut/tip kontrolü) kapsanır.
- Menü/tray entegrasyonu gerçek Windows masaüstünde manuel doğrulanır (bu projede tüm
  OS-seviyesi entegrasyonlarda izlenen desen).

## Kapsam Dışı

- İkonun duruma göre (üretiyor/bekliyor) renk değiştirmesi — YAGNI, şimdilik tek durum.
- Gerçek bir marka logosu — ileride tasarım işi.
