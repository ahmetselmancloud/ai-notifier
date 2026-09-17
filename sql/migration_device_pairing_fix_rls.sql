-- Task 6 canlı testinde bulundu: authenticated rolü için pairing_codes'ta hiç
-- SELECT ilkesi yoktu. Bu, claim sonrası güncellenen satırı geri okuyamadığımız
-- (ve dolayısıyla gerçek başarı/başarısızlığı ayırt edemediğimiz) için
-- web/app/pair/claim/page.tsx'teki .update() çağrısının sonucunu doğru
-- değerlendirememesine yol açtı.

create policy "authenticated can read pairing codes"
  on pairing_codes for select
  to authenticated
  using (true);
