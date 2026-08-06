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

- [x] Supabase SQL Editor'da `RUN_IN_SUPABASE_SQL_EDITOR.sql` içindeki şu
      blokların prod'da uygulandığını doğrula, eksikse çalıştır:
      `chat_threads`, `idol_personas` + `persona_chunks`, `users.gender`
      (migration `20260728100000_faz8_gender.sql`).
- [x] Doğrulama sorgusu: `select table_name from information_schema.tables
      where table_schema='public';` → chat_threads, idol_personas,
      persona_chunks görünmeli; `select column_name from
      information_schema.columns where table_name='users';` → gender görünmeli.
- [x] API sertifikası: `test_two_plan_switch_certification_five_times` —
      Entelektüel ↔ Sporcu, 5 geçiş, aktif plan + vision board karışmaz
      (`tests/test_multi_plan.py`).
- KAPI: Gerçek cihazda (dev hesabı) iki plan oluştur → aralarında 5 kez
  geçiş yap → sohbet geçmişi ve vision-board görselleri her planda doğru.
  *(API yeşil; cihaz smoke Şahin'e bırakıldı.)*

### 8.2 — Gemini 3.1 Pro geçişi (yarım gün) — MODEL SEÇİLDİ (2026-07-29)

Şahin'in kararı: sohbet + plan artık **`gemini-3.1-pro-preview`** (kimlik
ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview'dan doğrulandı;
1M giriş / 65K çıkış, function calling + yapısal JSON + görüntü girişi destekli).
Kod tarafı HAZIR: config varsayılanları güncellendi; Gemini 3'te
`thinking_budget=0` geçersiz olduğundan client `thinking_level="low"` kullanıyor
ve fallback'te config yeniden kuruluyor (`gemini_client._build_config`).

**Prod Railway (api) — 2026-07-29:**
- Ana: `GEMINI_MODEL=gemini-3.1-pro-preview`,
  `GEMINI_MODEL_PLAN=gemini-3.1-pro-preview`
- Fallback (SİLİNMEZ): `GEMINI_FALLBACK_MODEL=gemini-2.5-flash`,
  `GEMINI_FALLBACK_MODEL_PLAN=gemini-2.5-pro`
- `RAG_CHAT_EMBEDDINGS=false`

- [x] Railway → Variables: ana model 3.1-pro-preview; 2.5 fallback'ler korundu.
- [x] `/health` → `model_chat`/`model_plan` = `gemini-3.1-pro-preview` (2026-07-29).
      Cihazda 1 sohbet + 1 plan + 1 kanıt smoke Şahin'e bırakıldı.
- [ ] ⚠️ KOTA / PAID TIER: 3.1 Pro preview ücretsiz katman ~250 istek/gün —
      dev/demo için yeter, **LANSMANDA YETMEZ**. Google AI Studio / Cloud'da
      faturalandırmayı aç (paid tier) ve PostHog'da günlük Gemini istek
      sayısını izle. Kota bitince fallback 2.5'e düşer (yanıt gelir ama
      kalite düşer) — log'da "fallback" ara.
- KAPI: Sohbet yanıtı gerçek cihazda < 8 sn; yanlış model adı senaryosunda
  log'da "fallback" görülüp yanıtın yine gelmesi.

### 8.3 — Plan düzenleme: kullanıcı takvimi kişiselleştirebilsin (2-3 gün)

Kullanıcı Niyetsen'in görsel kimliği içinde kalarak görevleri taşıyabilmeli,
düzenleyebilmeli, ekleyip silebilmeli.

- [x] Backend: `PATCH /plan/tasks/{task_id}`, `POST /plan/days/{date}/tasks`,
      `DELETE /plan/tasks/{task_id}` — `plan_edit_service` + 13 test.
      (Şemada `time` yok → title+date; geçmiş/done engelli.)
- [x] Mobil: Planım/Bugün uzun bas → Taşı / Düzenle / Sil + temalı tarih;
      `plan-task-editor.tsx` + api helpers; + Görev ekle. Vision-board aynı.
- [x] Kural (backend): geçmiş güne taşınamaz; tamamlanmış düzenlenemez.
- KAPI kalan: cihaz smoke (yarına taşı → cron/puan); tsc 0 ✅; plan_edit 13 ✅.

### 8.4 — Profil ekranı gerçek app hissi + cinsiyet UI + burç ikonu (1-2 gün)

- [x] `settings.tsx` kompakt mobil hiyerarşi (avatar + isim + burç glyph).
- [x] Burç: `zodiacLabel` / `zodiacFromBirthDate` + isim yanı glyph.
- [x] Cinsiyet chip’leri + onboarding atlanabilir adım (aynı 3 string).
- [x] Mistik hub/tarot/fal/astro başlıklarında burç; `mystic-screen-shell`.
- KAPI kalan: cihazda cinsiyet → sohbet hitap smoke (Şahin); tsc 0 ✅.

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

- [x] `proof_service` + `PROOF_VALIDATION_PROMPT` GÖREV BAĞLAMI: plan adı,
      gün teması, aynı gün kardeş görevler, image_keyword; `routes.upload_proof`
      doldurur (`tests/test_proof_context.py`). Cihaz smoke Şahin.
- [ ] Sınır vakalarla cihaz testi: su bardağı ≠ meyve tarifi (RED),
      gerçek tabak (ONAY), ekran görüntüsü (RED), loş/yakın çekim (nazik tekrar).
- KAPI: Su fotoğrafı meyve görevini GEÇEMEZ; meşru fotoğraf ≥60 güvenle geçer;
  3 deneme + beyan kuralı (MASTER_PLAN §1.5) bozulmaz.

### 8.8 — Niyetsen Raporu "Wrapped" (1-1,5 gün; yazılımcı talebi, 28 Tem)

Spotify'ın yıllık özeti gibi: 14 günlük (ve aylık) dönem sonunda kullanıcı
story formatında görür — kaç görev yaptı, hangi karakter özellikleri gelişti,
başladığından beri yolculuğu.

İSKELET HAZIR (2026-07-29, Claude Cowork):
- Backend: `services/recap_service.py` (kural bazlı, Gemini yok — hız/kota) +
  `GET /me/recap?period=14d|30d` + `RecapCard/RecapResponse` şemaları +
  `recap_push_body()` bildirim kopyası. 4 test yeşil (`test_recap.py`).
- Mobil: `src/app/rapor.tsx` story ekranı (ilerleme çubukları, dokun-ilerle,
  5 kart: intro/tasks/trait/streak/closing) + `api.ts getRecap`.
- Tasarım kuralı: Wrapped mantığı = YALNIZ kazanımlar. Kaçırılan görev sayısı
  raporda GÖSTERİLMEZ (Spotify az dinlediğini yüzüne vurmaz; ton kuralı).

Cursor görevleri:
- [x] Giriş noktası: `rank.tsx` üstüne "Raporun hazır ✨" banner'ı — kullanıcı
      14. günü geçtiyse görünür (days_in >= 14), `router.push('/rapor')`.
- [x] Push: notification_service'e 14. gün (ve sonrasında her 30 günde bir)
      `recap_service.recap_push_body()` ile bildirim; data payload'ına
      `{"screen": "rapor"}` → bildirime dokununca /rapor açılır (deep link).
- [x] Story cilası: kart geçiş animasyonu (Reanimated, Easing yalnız
      reanimated'dan), kind'a göre şablon (trait kartında kategori rozeti,
      streak kartında filiz 🌱→🌿→🌳), uzun basınca duraklat.
- [x] Paylaş: closing kartına "Paylaş" butonu (react-native-view-shot ile
      kart görüntüsü → native share sheet) — organik büyüme kanalı.
- [x] Aylık dönem: period=30d seçeneği UI'da (segment).
- KAPI: 14+ günlük dev hesabında rapor gerçek verilerle akıyor; boş/yeni
  kullanıcıda çökmüyor (kartlar dolu geliyor); reduce-motion'da sorunsuz.

### 8.9 — Çalışırlık turu (2026-08-05, Claude Cowork — Şahin'in canlı hata listesi)

**Tanılar + kod tarafında YAPILANLAR (yeniden yazma, üzerine inşa et):**

1. **Mistik çalışmıyor → KÖK NEDEN BULUNDU ve DÜZELTİLDİ:** `mystic.tsx`
   `openModule` her modülü (tarot/astroloji/fal/geçmiş) paywall'a
   yönlendiriyordu. KİLİTLİ KARARA aykırı regresyon: fal ÜCRETSİZ katmanda
   paywall'suzdur, hak sayaçları sunucuda, premium yalnız EK hak açar.
   Yönlendirme + ProBadge'ler kaldırıldı. Fal modüllerine paywall kapısı
   GERİ EKLENMEZ (İdol/yollar ayrı — o premium kalır).
2. **"Yeni plan oluştur → sohbete bağlanmıyor":** backend sözleşmesi uçtan uca
   test ile KANITLANDI (`tests/test_new_plan_chat_flow.py`): /projects/new →
   temiz /chat/session → /chat intent modunda yanıt + eski plan sohbeti
   sızmıyor. Bellek-içi akış kusursuz ⇒ canlıdaki kırılmanın 1 numaralı
   şüphelisi PROD SUPABASE'DE chat_threads MİGRATION'ININ EKSİK OLMASI
   (8.1 hâlâ kapanmadı — İLK İŞ). Cihazda tekrar ederse: Railway logunda
   /chat/session yanıtına bak, mobile'da focus-yenileme zaten var.
3. **Rapor gerçek veri ("verilerimi raporlayamıyor") → DÜZELTİLDİ:**
   `build_recap` artık TÜM planları toplar (routes tüm plan özetlerinden
   içerikli planları yükler), yolculuk EN ESKİ planın gününden sayılır,
   "trait" kartı dönem-GERÇEK veridir (o dönemde tamamlanan görevlerin
   kategorileri; boşsa tüm zaman puan lideri), görev kartı kanıtlı görev
   sayısını söyler, çoklu planda intro "N niyeti birden yürütüyorsun" der.
   Testler: `test_build_recap_aggregates_all_plans_and_period_trait`.
4. **İdol detay temeli → EKLENDİ:** `GET /paths/{slug}` (PRO kapılı,
   `_require_pro_modules`) — dossier'den güvenli bölümler: core_beliefs,
   mindset, habits, daily_routine, decision_style, failure_and_recovery,
   lessons_for_users, books. `public_quotes` BİLEREK dışarıda (yasal gri
   alan). Mobil istemci hazır: `api.ts getPathDetail` + `PathDetail` tipi.

**Cursor görevleri (UI detaylandırma):**
- [ ] İdol detay ekranı `src/app/yol-detay.tsx`: yollar.tsx karttan
      `getPathDetail(slug)` ile aç; sections listesi başlık+madde olarak
      MysticColors/İlkbahar hibrit kartlarda; source_note ekran altında
      küçük ve DAİMA görünür (yasal). "Bu yolu planıma uygula" CTA →
      mevcut yol seçim akışına bağlanır.
- [ ] Rapor kart şablonları zenginleştirme: trait kartında CategoryBadge +
      dönem sayısı; journey kartında Gün 1 → Gün N çizgisi; intro'da çoklu
      plan rozeti. Veri artık gerçek — UI onu göstersin.
- [ ] Backend testleri 207 yeşil — düşürme. `pytest -q` + `npx tsc --noEmit`.

### 8.10 — Minimal UI + "Kapı İçeride" (2026-08-05, Claude Cowork)

Şahin geri bildirimi: "her şey çok hantal, çok kalın, çok büyük — daha
minimalist" + "ücretli bölümleri ücretsiz kullanıcı da GÖRMELİ, dışarı
atılmamalı".

**Koda entegre EDİLDİ:**
- [x] **Minimal tipografi ölçeği (KİLİTLİ):** `themed-text.tsx` — title 44→32,
      screenTitle 28→22, subtitle 30→18. Tek dosya, tüm uygulama inceldi.
      Vurgu puntoyla değil boşluk/renkle verilir. Ölçeği BÜYÜTME.
- [x] **"Kapı İçeride" deseni:** rapor.tsx artık ücretsiz kullanıcıyı paywall'a
      ATMIYOR — ekran açılır, kilitli önizleme kartı (değer vaadi + "PRO ile
      aç" CTA) gösterilir. `useRequirePremium` yönlendirmesi bu ekrandan
      kaldırıldı; sunucu 402 son sözü söyler.
- [x] **Tasarım skill'i:** `.cursor/skills/niyetsen-tasarim/SKILL.md` —
      tipografi tablosu, İlkbahar token kuralları, kapı-içeride deseni,
      7 maddelik ekran QA listesi. HER UI işinde bu skill uygulanır.

**Cursor görevleri:**
- [ ] Kapı-içeride desenini kalan PRO yüzeylerine uygula (İdol/yol-detay,
      varsa diğer useRequirePremium kullanıcıları) — rapor.tsx örnek.
- [ ] Minimal ölçek sonrası ekran turu: dev başlık/boşluk artıkları
      (özellikle settings, dil seçici, mystic hub) — niyetsen-tasarim
      skill'indeki QA listesiyle ekran ekran geç.
- [ ] Dil seçici kompaktlaştır: tam liste yerine tek satır (mevcut dil +
      chevron) → seçim bottom sheet'te.

### 8.11 — Cihaz testi geri bildirimi (2026-08-05 akşam, Şahin — KRİTİK)

**Büyük gerçek:** Şahin'in test ettiği Play kapalı sürümü ESKİ build —
son haftaların hiçbir düzeltmesi içinde yok. İlk iş: push → yeni EAS build
(`eas build --profile play-internal --platform android`) → dahili teste yükle.

**Koda giren düzeltmeler (Claude Cowork):**
- [x] **Consent hızlı yolu:** her açılıştaki "Yasal tercihler kontrol
      ediliyor…" beklemesi bitti — onay bir kez verildiyse cache'ten anında
      geçilir, sunucu arka planda doğrular; yasal sürüm artarsa gate otomatik
      döner (`consent-gate.tsx`).
- [x] **Çökme tanı rehberi:** `docs/ANDROID_CRASH_TANI.md` — adb logcat
      yakalama komutu + elenen/açık şüpheli listesi. Kesin kök logcat'le bulunur.
- [x] i18n iskelet tanısı: `Copy.` kullanan 8 çekirdek dosya listelendi.

**Şahin'in çökme hipotezi (2026-08-05 akşam):** "Backend beynimiz çökme
nedeni." Canlı kontrol (Claude, aynı akşam): `/health` = ok, env=prod,
model=gemini-3.1-pro-preview — beyin ŞU AN ayakta. Ama Railway'in kesinti
geçmişi var → hipotezin güçlü hali: **test anında backend yerdeyse ve ESKİ
build açılışta API hatasını yutamıyorsa, uygulama kapanır.** Bu yüzden
8.11.0 görevi eklendi.

**Cursor görevleri (SIRAYLA):**
- [ ] 8.11.0 **Açılış dayanıklılığı (backend ölüyken bile açılan uygulama):**
      uygulamanın boot zincirini tara (_layout provider'ları, splash sonrası
      ilk fetch'ler) — HİÇBİR açılış isteği reddedilince ekranı/uygulamayı
      düşürmemeli: her boot fetch'i try/catch + "çevrimdışı görünüm" (önbellek
      + nazik banner "Bağlantı kurulamadı — tekrar dene"). KAPI: uçak modunda
      uygulama açılır, sekmeler gezilir, banner görünür, crash yok.
- [ ] 8.11.1 **i18n iskelet göçü:** şu 8 dosyada `Copy.*` → `useLocale().t.*`:
      `app/index.tsx`, `app/daily.tsx`, `app/paywall.tsx`, `app/rank.tsx`,
      `app/explore.tsx`, `components/chat-composer.tsx`,
      `components/plan-task-editor.tsx`, `components/chat-header.tsx`.
      Eksik anahtarları `i18n/catalog`'a ekle (TR birebir mevcut metin).
      KAPI: dil değiştirince TÜM sekme içerikleri değişir.
- [ ] 8.11.2 RTL kontrolü: `I18nManager.forceRTL` yalnız restart uyarısıyla;
      Arapçada açılış döngüsü testi (logcat).
- [ ] 8.11.3 "Öylesine duran" ekran avı: her ekranda ölü buton/boş dokunuş
      taraması — niyetsen-tasarim skill QA listesi madde 5 (yükleniyor/boş/
      hata) her ekrana uygulanır. Ölü yüzey = ya bağla ya kaldır.
- [ ] 8.11.4 Şahin logcat çıktısını getirince: ANDROID_CRASH_TANI şüpheli
      listesiyle eşleştir, kökü kapat, yeni build.

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
- Public zincir/rank, şehirler arası rekabet, store sonrası herkese açık
  istatistik → MASTER_PLAN **leaderboard v3**; FAZ 8 lansmanında kodlanmaz
  (puan/rank kullanıcı bazlı kalır; plan değişince score sıfırlanmaz).
