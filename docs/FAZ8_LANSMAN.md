# FAZ 8 — AĞUSTOS LANSMANI (Cursor için tam görev listesi)

> Kaynak: 28 Temmuz 2026 yatırımcı toplantısı geri bildirimi (Şahin).
> Ana iskelet 2026-07-29'da koda entegre edildi (Claude Cowork). Bu doküman
> Cursor Composer'ın FAZ 8 boyunca tek referansıdır. Sıra ATLANMAZ; her
> maddenin KAPI kriteri geçmeden sonraki maddeye geçilmez.
> Kilitli kararlar (MASTER_PLAN §1) ve CLAUDE.md kuralları aynen geçerli.

## Toplantıda tespit edilen sorunlar (demo hataları)

1. Sohbet yavaş ve kendini tekrar ediyor.
2. Sohbet sırasında plan OLUŞTURULAMADI (dev hesabı kutluadalarr7@gmail.com ile bile).
3. Planlar arası geçiş çalışmıyor (entelektüel plan ↔ sporcu planı).
4. Kanıt doğrulama fazla gevşek: su içme fotoğrafı "sağlıklı meyve/protein
   tarifi" görevini onaylattı.
5. Profil ekranı web sitesi gibi duruyor (dev başlıklar), gerçek app hissi yok.
6. Uygulama kullanıcının cinsiyetini bilmiyor → sohbet kişiselleşemiyor.
7. Burç ikonu yok; rehber mistik/normal sohbette kullanıcının burcunu tanımalı.
8. Bildirimler fazla yumuşak; kullanıcı gevşediğinde dürüst yüzleşme gerek.
9. Modeller yetersiz ("2.5 flash/pro gerçekten yaramıyor") → Gemini 3 ailesine geçiş.

## İskelette HAZIR olanlar (koda entegre, 2026-07-29)

| Sorun | Çözüm | Dosya |
|---|---|---|
| Hız | Sohbette sorgu embedding kapalı (keyword eşleşme), `RAG_CHAT_EMBEDDINGS=false` | `config.py`, `rag_service.py` |
| Model yükseltme | `GEMINI_FALLBACK_MODEL(_PLAN)` + `_is_model_unavailable` → geçersiz model adında otomatik geri dönüş | `config.py`, `core/gemini_client.py` |
| Plan güvencesi | `FORCE_PLAN_MARKERS` ("planı oluştur" vb.) → varsayılan doldurma + kesin ready; `generate_batch` not-ready'de artık hata atmaz | `services/intent_service.py`, `services/plan_service.py` |
| Plan geçişi / thread | chat_threads işlemleri degrade modda (try/except) — thread hatası sohbeti/geçişi düşüremez | `storage/supabase_repository.py` |
| Kanıt gevşekliği | `PROOF_VALIDATION_PROMPT` 6 katı kural: anlamsal eşleşme zorunlu, aynı-tema ≤40 güven, ekran görüntüsü/stok red | `core/prompts.py` |
| Cinsiyet | `users.gender` kolonu + şemalar + bellek bloğu "Cinsiyet:" satırı + SYSTEM_PROMPT klişesiz uyarlama kuralı; sohbet + fal uçtan uca | `schemas.py`, `profile_service.py`, `prompt_builder.py`, `prompts.py`, `intent_service.py`, `routes.py`, migration `20260728100000_faz8_gender.sql` |
| Burç ikonu | 12 sembollük harita + helper (UI yerleşimi Cursor'da) | `mobile/src/constants/zodiac.ts` |
| Bildirim tonu | `emotional_penalty_body` dürüst-direkt ("Disiplinin düşüyor… neden şimdi vazgeçesin?") | `services/push_service.py` |

## Cursor görevleri (SIRAYLA)

### 8.1 — Prod Supabase doğrulaması ⚠️ İLK İŞ (yarım gün)

Demo'daki "plan geçişi çalışmıyor" hatasının 1 numaralı şüphelisi: prod
veritabanında `chat_threads` migration'ının hiç çalıştırılmamış olması
(kod thread'e yazmaya çalışıp patlıyordu; degrade mod artık koruyor ama
tablo yine de gerekli).

- [ ] Supabase SQL Editor'da `RUN_IN_SUPABASE_SQL_EDITOR.sql` içindeki şu
      blokların prod'da uygulandığını doğrula, eksikse çalıştır:
      `chat_threads`, `idol_personas` + `persona_chunks`, `users.gender`
      (migration `20260728100000_faz8_gender.sql`).
- [ ] Doğrulama sorgusu: `select table_name from information_schema.tables
      where table_schema='public';` → chat_threads, idol_personas,
      persona_chunks görünmeli; `select column_name from
      information_schema.columns where table_name='users';` → gender görünmeli.
- KAPI: Gerçek cihazda (dev hesabı) iki plan oluştur → aralarında 5 kez
  geçiş yap → sohbet geçmişi ve vision-board görselleri her planda doğru.

### 8.2 — Gemini 3 geçişi (yarım gün)

- [ ] https://ai.google.dev/gemini-api/docs/models adresinden GÜNCEL kararlı
      model adlarını doğrula (Gemini 3 ailesi: flash sınıfı sohbet/vision,
      pro sınıfı plan üretimi). Model adı UYDURMA — sayfadaki adı birebir al.
- [ ] Railway → Variables: `GEMINI_MODEL` ve `GEMINI_MODEL_PLAN`'ı yeni
      adlarla değiştir. `GEMINI_FALLBACK_MODEL=gemini-2.5-flash`,
      `GEMINI_FALLBACK_MODEL_PLAN=gemini-2.5-pro`, `RAG_CHAT_EMBEDDINGS=false`
      değişkenlerini ekle. Kod değişikliği GEREKMEZ.
- [ ] `/health` yanıtında model adlarını gör; 1 sohbet + 1 plan üretimi smoke test.
- KAPI: Sohbet yanıtı gerçek cihazda < 8 sn; yanlış model adı senaryosunda
  log'da "fallback" görülüp yanıtın yine gelmesi.

### 8.3 — Plan düzenleme: kullanıcı takvimi kişiselleştirebilsin (2-3 gün)

Kullanıcı Niyetsen'in görsel kimliği içinde kalarak görevleri taşıyabilmeli,
düzenleyebilmeli, ekleyip silebilmeli.

- [ ] Backend endpoint'leri (JWT + rate limit, şema MASTER_PLAN §2):
      `PATCH /plan/tasks/{task_id}` (title/date/time düzenleme),
      `POST /plan/days/{date}/tasks` (kullanıcı görevi ekleme, +50 puan
      kuralına dahil), `DELETE /plan/tasks/{task_id}` (yalnız pending,
      ceza tetiklemez). Görev taşıma = PATCH ile date değişimi.
- [ ] Mobil: takvim/plan ekranında görev kartına uzun basınca "Taşı / Düzenle /
      Sil" action sheet; tarih seçici Niyetsen temasında. Vision-board
      görselleri ve kart tasarımı DEĞİŞMEZ.
- [ ] Kural: geçmiş güne görev taşınamaz; tamamlanmış görev düzenlenemez.
- KAPI: Cihazda görev yarına taşınır → cron/puan akışı bozulmaz; testler yeşil.

### 8.4 — Profil ekranı gerçek app hissi + cinsiyet UI + burç ikonu (1-2 gün)

- [ ] `mobile/src/app/settings.tsx` (Profil) yeniden düzenle: dev web başlıkları yerine kompakt mobil
      hiyerarşi (avatar + isim satırı, küçük bölüm başlıkları, kart listeleri).
      Mevcut tema token'ları kullanılır; YENİ tasarım dili İCAT ETME.
- [ ] İsim yanına burç ikonu: `zodiacLabel(profile.zodiac_sign)`
      (`mobile/src/constants/zodiac.ts` hazır).
- [ ] Cinsiyet seçimi: profil düzenlemede 3 seçenek — "kadın", "erkek",
      "belirtmek istemiyorum" (backend Literal ile birebir aynı string'ler).
      Onboarding'e de nazik, atlanabilir bir soru olarak ekle.
- [ ] Mistik ekranlarda (tarot/astroloji/fal) kullanıcının burç sembolü
      başlıkta görünsün (rehber zaten bellek bloğundan tanıyor).
- KAPI: iPhone SE + büyük Android'de taşma yok; tsc 0 hata; cinsiyet seçimi
  kaydedilip sohbette hitabın değiştiği gözlemleniyor.

### 8.4-B — UI v3 "İLKBAHAR" ekran turu (paralel şerit, 8.4 ile birlikte)

Yatırımcı geri bildirimi: "Arayüz pastel; uygulama ilkbaharı hissettirmeli,
sonbaharı değil." Palet iskeleti (Adım 0) koda entegre edildi — tüm token
değerleri yenilendi (`theme.ts`), uygulama otomatik canlandı. Kalan ekran
turu ve mikro-etkileşim sözlüğü: **`docs/UI_V3_ILKBAHAR.md`** (Adım 1-7,
her adımın KAPI'sı orada). 8.4 profil işi bu dille yapılır.

### 8.5 — Çoklu plan geçişi uçtan uca sertifikasyon (1 gün)

- [ ] 8.1 sonrası: iki farklı karakterde plan (entelektüel + sporcu) oluştur;
      geçişte doğrula: aktif plan, günün görevleri, vision-board görselleri,
      sohbet thread'i, puan/zincir ekranı.
- [ ] Geçiş hatalarını Sentry'ye breadcrumb'la bağla (`set_active_plan`
      degrade moda düştüğünde warning event).
- KAPI: 10 ardışık geçişte sıfır hata; yanlış plan verisi sızması yok.

### 8.6 — Kanıt doğrulamada kişisel görev bağlamı (1 gün)

Sıkı prompt entegre; eksik parça: görevin KİŞİSELLEŞTİRİLMİŞ içeriği
(ör. plandaki tarifin malzemeleri) modele gitmiyor.

- [ ] `proof_service` çağrısında Gemini Vision'a görev başlığı + görev
      açıklaması + (varsa) plan günü bağlamını geçir; prompt'taki
      "GÖREV BAĞLAMI" alanını doldur.
- [ ] Sınır vakalarla cihaz testi: su bardağı ≠ meyve tarifi (RED),
      gerçek tabak (ONAY), ekran görüntüsü (RED), loş/yakın çekim (nazik tekrar).
- KAPI: Su fotoğrafı meyve görevini GEÇEMEZ; meşru fotoğraf ≥60 güvenle geçer;
  3 deneme + beyan kuralı (MASTER_PLAN §1.5) bozulmaz.

### 8.7 — Lansman kontrol listesi (2-3 gün, store bekleme hariç)

- [ ] Store metinleri güncelle (fal İKİNCİL özellik — Apple 4.3 riski).
- [ ] IAP smoke test: RevenueCat sandbox satın alma + restore + webhook.
- [ ] PostHog hunisi: onboarding → ilk plan → ilk kanıt → D1/D7 retention.
- [ ] Sentry alarmları: 5xx oranı + Gemini fallback sayacı.
- [ ] `notification_service` kopya gözden geçirme: 8'deki dürüst ton diğer
      hatırlatıcılarla tutarlı mı (utandırma çizgisi ASLA aşılmaz).
- KAPI 8 (fazın çıkış kapısı): yeni kullanıcı sohbeti <8 sn, "planı oluştur"
  %100 plan üretir, 2 plan arası geçiş + görseller sorunsuz, su içme fotoğrafı
  meyve görevini geçemez. Hepsi yeşilse → store'a gönder.

## Değişmeyen kurallar (hatırlatma)

- Puan/ceza/zincir sayıları: MASTER_PLAN §1–2 birebir. Taban 0, tavan 200.
- Ton: dürüst yüzleşme ✅ ("Disiplinin düşüyor, neden vazgeçiyorsun?"),
  aşağılama/utandırma ❌ ("tembelsin", "yine yapmadın").
- Cinsiyet = ince uyarlama sinyali; klişe/genelleme YASAK (prompts.py kuralı).
- Sırlar yalnız .env; migration'lar önce SQL Editor'da; her ekran gerçek cihazda.
- Araç listesi dışına çıkma (core/tools.py).
