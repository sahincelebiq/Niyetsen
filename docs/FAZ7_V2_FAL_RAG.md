# FAZ 7 — v2: Fal Modülü + RAG (AKTİF)

> Başlangıç: 2026-07-16, Şahin'in talimatıyla (Claude Cowork ilk dalgayı inşa etti).
> Tek gerçek kaynak sırası: `NIYETSEN_MASTER_PLAN.md` §1–2 → bu dosya.
> Cursor: oturuma başlarken burayı ve MASTER_PLAN FAZ 7 bölümünü oku.

## Ne inşa edildi (Dalga 1 — 2026-07-16)

### RAG altyapısı
- **Bilgi tabanı:** `niyetsen-backend/knowledge/*.md` — tarot (22 Büyük Arkana,
  anlamlarıyla), burçlar (12 burç + elementler), motivasyon, atomik alışkanlıklar,
  felsefe (philosophy.py'nin RAG sürümü). Kaynak docx'ler repo kökünde duruyor;
  **markdown kopyalar tek gerçek kaynak** (Railway'e deploy edilen bunlar).
- **`app/services/rag_service.py`:** başlık bazlı chunking (≤900 karakter),
  Gemini `gemini-embedding-001` + kosinüs benzerliği, süreç içi önbellek.
  Anahtar yoksa / embedding hata verirse **keyword fallback** (testler ağsız).
  Chroma bilinçli olarak requirements'a eklenmedi (Railway imajı); istenirse
  `pip install chromadb` + backend yuvası açılır.
- **Sohbet entegrasyonu:** `intent_service.handle_chat` → `retrieve_for_chat`.
  Varsayılan kaynaklar: felsefe + motivasyon + atomik_aliskanliklar (rehber
  kişisel gelişim bağlamıyla konuşur — Şahin'in 2026-07-16 isteği). Kullanıcı
  tarot/burç açarsa ilgili kaynak eklenir. RAG içeriği HER ZAMAN etiketli
  CONTEXT bloğunda (`[BİLGİ TABANI …]`) — kullanıcı mesajıyla karışmaz.
- Env anahtarları (`.env.example`'da): `RAG_ENABLED=true`,
  `RAG_EMBEDDINGS_ENABLED=true`, `RAG_TOP_K=4`, `GEMINI_EMBED_MODEL`.

### Fal modülü
- **`app/services/fortune_service.py`** + `prompts.FORTUNE_SYSTEM_PROMPT`
  (ikinci, duygusal system prompt — fal AYNA'dır, kader değil; korku satmak,
  tıbbi/finansal/hukuki tavsiye yasak; her yorum en küçük halkaya bağlanır;
  kriz sinyalinde fal durur ve desteğe yönlendirir).
- **Tarot:** günlük 1 çekim (herkes), 3 kart (geçmiş/şimdi/niyetin yönü),
  %30 ters olasılığı, deste `knowledge/tarot.md`'den ayrıştırılır (22 kart).
  Aynı gün ikinci istek kayıtlı sonucu döner (idempotent). Gemini çökerse
  statik kart anlamlarıyla fallback yorum — endpoint asla boş dönmez.
- **Kahve/El:** `gemini-2.5-flash` Vision → `{is_valid_photo, symbols,
  interpretation}`. Yanlış fotoğraf (telve/avuç yok) **hak yakmaz** (kanıt
  akışıyla aynı ilke). 5MB/jpeg-png doğrulaması proof ile aynı; in-app kamera.
- **Burç:** profildeki `zodiac_sign` (yoksa doğum tarihinden); günlük önbellek
  (`fortune_log`) — sınırsız ama Gemini'ye günde 1 çağrı (maliyet).
- **Hak sayaçları** (algoritma §5, `config.FORTUNE_DAILY_RIGHTS`):
  el 1 (premium 3) · kahve 1 (premium 3) · tarot 1 (ek yok) · burç sınırsız.
  "premium" = `has_premium_access` (deneme süresi dahil). Not: belgedeki
  "kahve ücretli +ek" ifadesi +2 olarak yorumlandı — Şahin değiştirebilir.
- **Endpoint'ler** (hepsi JWT + rate limit 6/dk):
  - `GET /fortune/rights` — günlük hak durumu
  - `POST /fortune/tarot` `{question?}` — consent: chat
  - `POST /fortune/photo/{kahve|el}` (multipart photo) — consent: chat + proof_photo
  - `GET /fortune/horoscope` — consent: chat
  - Hak dolunca **429**, yanlış fotoğraf/kriz sinyali **400**, Gemini çökük **503**.
- **DB:** `fortune_log` (id, user_id, type, day, result_json, created_at;
  index user+type+day; RLS açık, erişim service_role). Migration:
  `supabase/migrations/20260716120000_faz7_fortune_log.sql`.

### Mobil (Expo)
- `src/lib/api.ts`: `getFortuneRights`, `drawTarot`, `getDailyHoroscope`,
  `uploadFortunePhoto` + tipler (backend şemasıyla birebir).
- `tarot.tsx`: çekim butonu → 3 kart + yorum; bugünkü çekim varsa otomatik yükler.
- `astroloji.tsx`: günlük burç otomatik; doğum tarihi yoksa profile yönlendirir.
- `fal.tsx`: kahve/el seçimi, kalan hak göstergesi, in-app kamera (daily.tsx
  deseniyle aynı), sonuç kartı + disclaimer.
- Her ekranda "eğlence amaçlıdır" disclaimer'ı görünür (store uyumu §1.8/риск radarı).

### Testler
- `tests/test_fortune.py` (18): çekim, idempotency, hak limitleri, ayrı sayaçlar,
  consent zorunluluğu, kriz durdurma, yanlış fotoğrafın hak yakmaması, burç
  önbelleği, rights endpoint'i.
- `tests/test_rag.py` (6): chunk yükleme, kaynak filtresi, sohbet kaynak seçimi,
  mistik tetikleyici, RAG kapalıyken boş dönüş.
- Toplam backend: **148 test yeşil**. Mobil `tsc --noEmit` 0 hata.

## Dalga 1.5 — UI optimizasyonu + senaryo tabanı (2026-07-16, aynı gün)
- `knowledge/senaryolar.md`: 16 gerçek kullanıcı senaryosu (motivasyon düşüşü,
  zincir kırılması, erteleme, öz-eleştiri, yoğun dönem, uyku/spor/sosyal/
  para/sınav hedefleri, telefon bağımlılığı, aşırı hevesli başlangıç,
  yalnızlık, sisteme öfke, kanıt sorunu, tatil). Sohbet varsayılan RAG
  kaynaklarına eklendi — rehber duruma göre doğru yaklaşımı çeker.
- Responsive düzeltmeleri: tarot/astroloji/fal ekranlarına tab bar inset'i
  (içerik tab bar altında kalıyordu), fal kamera ipucu metninde dar ekran
  taşması, 44pt dokunma hedefleri (mistik geri linkleri, paywall geri yükleme,
  explore "Planı değiştir", onboarding "Geri" hitSlop). Kaynak: tam ekran
  responsive taraması (375pt SE → 440pt Pro Max + Android çentik).

## Website bakımı (2026-07-16, tasarım/renk paleti korunarak)
- OG paylaşım görselleri sıkıştırıldı: 8,5MB → ~3,2MB (1200×630, 128 renk
  adaptif palet) — WhatsApp/Telegram önizleme sınırının güvenli tarafında.
- Favicon URL'leri mutlak (`https://niyetsen.com/...`) → göreli (`/favicon...`)
  — localhost/staging'de de çalışır (14 sayfa).
- `site.webmanifest` 512px ikonu `favicon-512x512.png`'ye bağlandı.
- index.html akış adımları h4 → h3 (başlık hiyerarşisi) + CSS selektörü.
- CSS/JS önbellek sürümleri `?v=20260716-1` olarak eşitlendi (tüm sayfalar).
- `gelistirme.html`: Faz 7 (v2) paralel koridoru + 16 Temmuz bakım kartı eklendi.
- `sitemap.xml` lastmod 2026-07-16. Denetim sonucu: kırık link 0, HTML hatası 0,
  JS `node --check` temiz. Erken erişim formu FormSubmit'e gider (backend'e değil).

## Şahin'in yapması gerekenler (kod dışı)
1. **Supabase SQL Editor'da** `RUN_IN_SUPABASE_SQL_EDITOR.sql` sonundaki
   fortune_log bloğunu çalıştır (veya migration dosyasını).
2. Railway'e push sonrası `/fortune/rights`'ı gerçek cihazdan dene.
3. İstersen `RAG_EMBEDDINGS_ENABLED=false` ile maliyetsiz (keyword) modda başlat.

## Dalga 3 öncesi güçlendirme (2026-07-17, ikinci tur)
- [x] **Store güvenlik katmanı** (`app/main.py`): 10MB mutlak gövde tavanı,
      güvenlik başlıkları (nosniff, X-Frame-Options DENY, Referrer-Policy,
      no-store, prod'da HSTS), işlenmeyen hatalarda iç detay sızdırmayan
      500 + Sentry/log.
- [x] **iOS export compliance**: `ITSAppUsesNonExemptEncryption=false`
      (app.json) — TestFlight yüklemelerinde şifreleme sorusu otomatik geçer.
- [x] **Hızlı yanıt çipleri**: ChatResponse.suggestions (≤3 kısa öneri) —
      model her sorusuyla tek dokunuşluk cevaplar üretir; mobil mevcut
      ChatQuickReplies bileşeniyle gösterir, dokunuş direkt gönderir.
      Plan sonrası sohbette de devam önerileri gelir.
- [x] **Plan tempo kuralları** (PLAN_JSON_INSTRUCTIONS): ilk 3 gün garantili
      kazanım, haftada 1 hafif gün, kademeli zorluk (+%10), zor gün sonrası
      toparlanma, kategori çeşitliliği, görevlerin birbirine zincirlenmesi —
      "kullanıcıyı yormadan potansiyele taşı".
- Doğrulama: backend 156 test, mobil tsc 0 hata.

## Sonraki dalgalar (öncelik sırasıyla)

### Dalga 2 — Fal UX tamamlama ✅ TAMAMLANDI (2026-07-17)
- [x] 06:01 "Günlük Tarot" push'u (algoritma §4) — `notification_service`'e
      `last_tarot_push_date` deseniyle eklendi (görev hatırlatıcısı +1 dk).
- [x] Tarot çekim animasyonu: yüzü kapalı deste sahnesi → kademeli FlipInEasyY
      kart açılışı → gecikmeli yorum FadeIn (Reanimated, yeni bağımlılık yok).
- [x] Fal geçmişi: `GET /fortune/history?limit=` + `fal-gecmisi.tsx` ekranı
      (tip rozetleri, genişleyen yorum; mystic hub kartları "Yakında"→"Keşfet"
      ve hub'a geçmiş bağlantısı eklendi).
- [x] Küçük Arkana 56 kart — knowledge/tarot.md dolduruldu; deste 78 kart
      (parser testi geçti).

### Dalga 2.5 — Sohbet kalitesi + platform ✅ (2026-07-17, Şahin'in ekran
görüntüleriyle bildirdiği sorunlara karşılık)
- [x] **Rehber tekrarları düzeltildi:** SYSTEM/GUIDE prompt'a "DOĞALLIK
      KURALLARI" eklendi: burçtan yalnız kullanıcı açarsa söz et, görev
      adlarını birebir alıntılamak yasak, açılış/kapanış kalıp tekrarı yasak,
      yalnız Türkçe ("pending" ❌ "bekleyen" ✅), önce sorulan soruya cevap.
      (Sorun: her mesajda "Yengeç burcunun verdiği azimle…" tekrarı.)
- [x] **Yeni Sohbet Başlat:** `POST /chat/reset` — aktif planın sohbet
      mesajlarını siler, plan/görev/puan korunur; drawer'da (☰) "Yeni Niyet
      Başlat"ın üstünde ikinci buton + onay diyaloğu. İstemci artık en fazla
      son 40 mesajı gönderiyor (uzun sohbet istek şişmesi bitti).
- [x] **Geliştirici hesabı:** `DEV_ACCOUNT_EMAILS` env (varsayılan:
      kutluadalarr7@gmail.com) — JWT'deki doğrulanmış e-posta eşleşirse
      abonelik kısa devresi (status=active, paywall yok). Normal
      kullanıcılar ve Expo Go testçileri standart deneme→paywall akışında;
      arayüzde geliştirici izi yok. `app/core/dev_accounts.py`.
- [x] Testler: **156 yeşil** (chat reset, dev hesabı, fal geçmişi dahil);
      mobil tsc 0 hata.

### Dalga 3 — RAG derinleştirme
- [ ] Chroma kalıcı backend (lokal `chroma_db/`) — opsiyonel bağımlılık olarak.
- [ ] Embedding disk önbelleği (Railway yeniden başlatmalarında yeniden
      embedding maliyetini kes).
- [ ] Burç yorumunda haftalık/aylık görünüm.

### Dalga 4 — v3 adayları (dokunma)
- Leaderboard, Pinterest görsel kaynağı (`image_service` sözleşmesi hazır),
  `harita_yer_getir` aracı.

## Model kullanım haritası (kontrol edildi, 2026-07-16)
| İş | Model | Nerede |
|---|---|---|
| Sohbet + niyet + fal yorumları | `gemini-2.5-flash` | `GEMINI_MODEL` |
| Plan üretimi (JSON, 8192 token) | `gemini-2.5-pro` | `GEMINI_MODEL_PLAN` (90s timeout artık aktif) |
| Kanıt + fal fotoğraf Vision | `gemini-2.5-flash` | `generate_json_with_image` |
| Plan görselleri (hibrit) | `gemini-2.5-flash-image` (Nano Banana) + Unsplash | `GEMINI_MODEL_IMAGE` |
| RAG embedding | `gemini-embedding-001` | `GEMINI_EMBED_MODEL` |
