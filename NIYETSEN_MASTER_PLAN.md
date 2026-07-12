# NİYETSEN — MASTER GELİŞTİRME PLANI (Cursor için)

> **Bu dosya nasıl kullanılır:** Bu dosyayı repo köküne koy. Cursor'a şunu söyle:
> *"NIYETSEN_MASTER_PLAN.md dosyasını oku. Faz 0'dan başla. Her fazın sonundaki
> KAPI kriterleri geçmeden bir sonraki faza GEÇME. Her görevi bitirince bu dosyada
> `[ ]` → `[x]` işaretle ve küçük bir commit at."*
>
> Eşlik eden dosyalar: `CLAUDE.md` (ajan çalışma kuralları), `docs/` altındaki
> planlama belgeleri, `prompts/chat_system_prompt.md`, `knowledge/` (RAG).
> Bu plan onlarla çelişirse **BU PLAN kazanır** — çelişkiler burada çözüldü (§1).

---

## §0. TEK CÜMLE

Niyetsen: kullanıcının "bu yıl nasıl bir hayat istiyorum" niyetini sohbetle alan,
görselli günlük oyunlaştırılmış plana çeviren, görevleri foto kanıtıyla yaptıran,
yapmayınca puan düşüren, fal/astroloji modüllü bir yaşam asistanı.
iOS + Android (Expo), backend Python/FastAPI, AI Gemini.

---

## §1. KİLİTLİ KARARLAR (eski belgelerdeki çelişkiler ve açıklar burada çözüldü)

Bu bölüm bağlayıcıdır. Cursor bu kararları sorgulamadan uygular.

### 1.1 Ücretsiz katman (ÇELİŞKİ ÇÖZÜLDÜ)
Eski belgelerde iki farklı tanım vardı ("3 sohbet + 1 kullanım" vs "ilk plan +
birkaç gün"). **Geçerli kural:**
- Ücretsiz: onboarding sohbeti + **ilk gerçek plan tam görünür** + **7 gün görev
  deneme** + günde 1 tarot çekimi.
- 7. günün sonunda paywall: aylık 450 TL veya yıllık 3.600 TL (aylık ~300 TL eşdeğeri).
- Gerekçe: "aha anı" yaşanmadan 450 TL ödenmez; kaybetme korkusu (7 günlük zincir +
  görünen plan) satışı yapar.

### 1.1.1 Çoklu plan projeleri (YENİ — 2026-07-12)
- **Free / deneme:** kullanıcı **yalnızca 1 plan** oluşturabilir — 7 günlük deneme
  süresinde bile ikinci plan yok. İkinci plan için **ödenmiş abonelik** (450 TL) gerekir.
- **Abone:** sınırsız yeni niyet başlatabilir; her niyet ayrı **plan slotu** (Plan 1,
  Plan 2…) olarak saklanır; kullanıcı isimlendirebilir.
- Sohbet geçmişi ve niyet toplama **aktif plan slotuna** bağlıdır (`plan_id`).
- Mobil: sohbet ekranında sol **geçmiş sohbet** ikonu → proje listesi + "Yeni Niyet
  Başlat"; Planım başlığına tıklayınca plan seçici + isimlendirme.
- Bugün ekranı: tüm planlardan bugünün görevleri plan adı etiketiyle listelenir.
- API: `GET /projects`, `POST /projects/new`, `PUT /projects/{id}/activate`,
  `PATCH /projects/{id}`, `GET /tasks/daily`.

### 1.2 Ceza katlanması (AÇIK KAPATILDI)
Eski algoritmada katlanma tavansızdı (25→50→100→200→400…). **Geçerli kural:**
- Sessiz kaçırma cezası: 25 → 50 → 100 → **200 (TAVAN)**. 200'ü aşmaz.
- Herhangi bir görev tamamlanınca `silent_miss_streak = 0`.
- **Puan hiçbir kategoride 0'ın altına inmez** (negatif puan yok).
- Mazeret yolu aynen: sabit 25, katlanmaz, sayaç sıfırlanır; 10 mazerette puan ×0.5.
- Gerekçe: tavansız katlanma + negatif puan "utandırmama" ilkesini bozar ve
  kullanıcıyı silmeye götürür.

### 1.3 Zincir (streak) tanımı (EKSİKTİ, TANIMLANDI)
- Zincir devam koşulu: o gün **en az 1 görev tamamlandı**.
- Gün sınırı: kullanıcının cihaz saat dilimi (varsayılan Europe/Istanbul), 23:59.
- **Zincir Koruma Jetonu:** ayda 1 adet otomatik verilir; hiç görev yapılmayan bir
  günde otomatik harcanır, zincir kırılmaz. (Aboneler ayda 2 jeton alır — v1.1.)
- Zincir kırılınca mesaj tonu: "yarın yeni bir halka" — asla suçlama.

### 1.4 Bildirim saati (DEĞİŞTİ)
- Sabit 06:00 kaldırıldı. **Varsayılan 08:00**, kullanıcı onboarding'de saat seçer.
- Görev bildirimi + 1 dk sonra Günlük Tarot bildirimi (çift bildirim düzeni korunur).
- iOS bildirim izni + Android 13+ POST_NOTIFICATIONS izni ayrı ayrı istenir;
  reddedilirse uygulama çalışmaya devam eder (in-app hatırlatıcı devreye girer).

### 1.5 Foto kanıt doğrulama (EKSİKTİ, TANIMLANDI)
- v1'de **yalnız uygulama içi kamera** (galeriden seçim YOK — sahtecilik önlemi).
- Doğrulama: foto + görev başlığı Gemini Vision'a gider → "bu foto bu görevi
  kanıtlar mı?" → 0–100 güven skoru döner.
  - skor ≥ 60 → onay + puan.
  - skor < 60 → nazik "tam emin olamadım, bir kare daha dener misin?" (maks 3 deneme,
    3. denemede kullanıcı beyanıyla kabul et — kullanıcıyla savaşma).
- Konum: opsiyonel; varsa skora +10 bonus güven.
- Fotolar Supabase Storage'da, kullanıcıya özel bucket, hesap silinince silinir.
- Yükleme limiti: 5 MB, sadece jpeg/png, sunucuda content-type doğrula.

### 1.6 Kimlik doğrulama (EKSİKTİ, TANIMLANDI)
- v1: Supabase Auth. Sağlayıcılar: **Apple ile Giriş + Google + e-posta**.
  (Apple kuralı: 3. parti login varsa Sign in with Apple ZORUNLU.)
- Mobil → backend her istekte Supabase JWT taşır; FastAPI middleware'i doğrular.
  **JWT'siz hiçbir endpoint'e erişim yok** (health hariç) — aksi halde herkes
  Gemini kotanı yakabilir.
- **Hesap silme:** ayarlarda "Hesabımı sil" ZORUNLU (App Store şartı). Tüm veri +
  fotolar + abonelik bağlantısı silinir.

### 1.7 Ödeme (NETLEŞTİ)
- Yalnız store içi satın alma (IAP) — RevenueCat ile. Harici ödeme linki YOK
  (Apple reddi sebebi).
- Paywall ekranında zorunlu öğeler: fiyat + yenileme koşulu + **"Satın alımları
  geri yükle"** butonu + Kullanım Koşulları ve Gizlilik Politikası linkleri.
- Deneme mantığı §1.1'e göre uygulama tarafında; store trial'ı kullanma
  (kontrol bizde kalsın).

### 1.8 KVKK / Gizlilik (EKSİKTİ, ZORUNLU)
- Gizlilik Politikası + Kullanım Koşulları sayfaları (basit statik web, domain
  altında). Store formlarında URL zorunlu.
- Toplanan hassas veri: foto, konum (ops.), doğum tarihi/burç, sohbet içeriği.
  Onboarding'de açık rıza metni + onay kutusu.
- Fal/astroloji içeriğinde kalıcı ibare: **"Bu içerik eğlence amaçlıdır; tıbbi,
  hukuki veya finansal tavsiye değildir."** (app içinde + store açıklamasında).
- Ruh sağlığı: chat guardrail'ine ek olarak backend'de kriz kelime filtresi →
  tetiklenirse model motivasyon modunu bırakır, profesyonel destek yönlendirmesi
  yapar (chat_system_prompt.md'deki kural + kod tarafında test).

### 1.9 AI dayanıklılık & maliyet (EKSİKTİ)
- Gemini çağrıları: chat için timeout 30 sn, 1 retry + `max_output_tokens=768`
  (gecikmeyi düşürür); plan üretimi için timeout 90 sn, `gemini-2.5-pro`,
  `max_output_tokens=8192`. Retry tükenince nazik hata ("Şu an yıldızlara
  ulaşamıyorum, birazdan tekrar dene ✨").
- **Çift model (2026-07-12):** `gemini-2.5-flash` = sohbet, araç çağrısı, kanıt
  vision; `gemini-2.5-pro` = yalnızca plan üretimi (`GEMINI_MODEL_PLAN`).
- Rate limit: kullanıcı başına dakikada 10 chat isteği (slowapi).
- Store yayını ÖNCESİ Gemini ücretli katmana geç (free tier 1.500 istek/gün canlıda
  yetmez).
- Prompt injection: kullanıcı mesajı asla system rolüne karışmaz; RAG içeriği
  CONTEXT bloğunda etiketli gider; model çıktısında function-call dışı araç
  denemesi reddedilir.
- Sohbet tonu: gereksiz övgü yok; mantıklı, önceki cevaba dayalı sorular.
- Kanıt vision: görev başlığı + `tiny_version` + kategoriler + `task_type` bağlamı
  prompt'a gider.
- Yeni/boş sohbet: `GET /chat/greeting` — kullanıcı timezone'una göre
  Günaydın / İyi günler / İyi akşamlar + isim.

### 1.10 Analitik (EKSİKTİ, YATIRIMCI İÇİN KRİTİK)
- Gün 1'den itibaren **PostHog** (ücretsiz katman yeter).
- Zorunlu event'ler: `app_open`, `onboarding_complete`, `first_plan_generated`
  (AHA anı), `task_completed`, `proof_uploaded`, `paywall_shown`,
  `subscription_started`, `subscription_cancelled`, `notification_opened`.
- D1/D7/D30 retention bu event'lerden ölçülür — yatırımcı hikâyesinin tamamı bu.

### 1.11 Görsel kaynak
- MVP + v1: Unsplash (lisans temiz). Pinterest v2'ye ertelendi (API onayı yavaş +
  app içinde gösterim ToS riski — v2'de hukuki kontrol yapılacak).
- Atıf UI (2026-07-12): görev kartında görsel üzerinde küçük ⓘ rozeti; uzun basınca
  fotoğrafçı metni + Unsplash linki. Metin DB'de kalır, ekranda gizlenir.

### 1.13 Sohbet UX (2026-07-12)
- Sabit üst header: ☰ menü her zaman erişilebilir (sohbet uzasa da kaydırma gerekmez).
- Sol kenardan sağa kaydırma: Niyetlerim paneli açılır (☰ ile aynı).
- Sohbet/plan senkronu: her niyet `plan_id` ile ayrı chat + intent; yeni niyet başlatınca
  temiz oturum + boş intent. Planı olan niyette "Planını Oluştur" gizlenir.
- Asistan balonu: zincir logosu (kutucuksuz metin); bekleme metni **düşünüyor…** +
  hafif zincir animasyonu.
- Dosya eki (v1): PDF/DOCX metin çıkarımı, PNG/JPEG kısa özet — `POST /chat/attachment`;
  mesaja `[Ek dosya: …]` olarak eklenir (max 5 MB).

### 1.12 İrade Modu — alarm kilidi (YENİ KARAR, 2026-07-07)
- Teknik gerçek: iOS/Android 3. parti uygulamaların sistem Saat/Alarm uygulamasına
  alarm eklemesine veya bir bildirimin ertelenmesini/kapatılmasını OS seviyesinde
  engellemesine izin vermiyor. "Fiziksel olarak erteleyememe" YOK.
- Bunun yerine: Ayarlar'da opt-in **"İrade Modu"** toggle'ı (kullanıcı kendi açar).
  Açıkken İrade/Disiplin kategorili görevlere `alarm_kur` ile yerel, tekrarlı/uzun
  sesli bildirim kurulur (gerçek OS alarmı DEĞİL, expo-notifications yerel bildirim).
- Süre içinde chat'te "yaptım" onayı gelmezse **yeni bir ceza mekanizması icat
  edilmez** — mevcut sessiz kaçırma akışı (§1.2, `scoring_service.py`) otomatik
  tetiklenir.
- Veri modeli eki: `users.irade_modu_active` (boolean, varsayılan false) — §2'de.
- Kapsam: FAZ 3'te (`alarm_kur` zaten o fazda planlı) inşa edilecek, şimdi
  kodlanmıyor — sadece karar kilitlendi.

### 1.13 Motivasyon Bonus-Görev Hub'ı (YENİ KARAR, 2026-07-07)
- Ana 7/365 günlük plana dahil DEĞİL; ayrı, foto kanıtı istemeyen "bonus görev"
  katmanı — CLAUDE.md'deki "plan uydurma, her görev kullanıcının anlattığı
  hayattan türer" kuralını ihlal etmemesi için ana plandan ayrı tutulur.
- İçerik: sabit, elle yazılmış ~20–30 maddelik Türkçe havuzdan (örn. 30 şınav,
  pencereyi aç oksijen al, köpeği gezdir, soğuk duşa gir) rastgele seçilir —
  Gemini çağrısı YOK, ekstra maliyet yok.
- Akış: push bildirimi → kullanıcı chat'te "yaptım" der → küçük sabit bonus puan
  (**+10**, normal görevin +50'sinden az — foto kanıtı olmadığı için güven skoru
  daha düşük varsayılır).
- Veri modeli eki: yeni tablo YOK — mevcut `point_log`'a `task_id=null`,
  `reason="bonus_micro_challenge"` ile yazılır (§2).
- Kapsam: FAZ 4'te (Expo Push altyapısının üzerine) inşa edilecek, şimdi
  kodlanmıyor — sadece karar kilitlendi. Yeni bir function-calling aracı
  gerekirse `tools.py`'daki KAPALI LİSTE kuralı gereği ayrıca onay istenecek.

---

## §2. VERİ MODELİ (Cursor bunu uydurmaz, buradan alır)

Supabase (Postgres). Dev'de lokal SQLite ile başlanabilir ama şema aynı kalır.

```
users        id (uuid, supabase auth), name, birth_date, zodiac_sign,
             timezone, notif_hour, created_at, subscription_status,
             excuse_count, freeze_tokens, irade_modu_active (bool, def. false),
             kvkk_consent_at (timestamptz, onboarding'de zorunlu)
intents      id, user_id, text, duration_days, status(active/done/abandoned),
             created_at
plans        id, intent_id, generated_json, created_at
tasks        id, plan_id, day_no, date, title, categories[], image_url,
             image_keyword, image_source, image_attribution,
             image_attribution_url,
             status(pending/done/missed_silent/missed_excused), proof_id?
proofs       id, task_id, photo_url, location?, confidence_score,
             attempt_no, created_at
points       user_id, category (6 sabit kategori), value  -- floor 0
point_log    id, user_id, task_id?, category, delta, reason, created_at
             -- reason="bonus_micro_challenge" + task_id=null: bonus-görev hub'ı
streaks      user_id, current_len, best_len, last_active_date,
             silent_miss_streak
chat_msgs    id, user_id, role, content, created_at   -- bellek için son N mesaj
fortune_log  id, user_id, type(tarot/kahve/el/burc), result_json, created_at  -- v2
```

6 kategori sabit: İrade · İstikrar · Disiplin · Özgüven · Sosyallik · Özsaygı.
Rank merdiveni: 1000 Bronz III → … → 10000 Usta (docs/uygulama-promt.md §6 tablosu).
Puan: görev +50; sessiz kaçırma −25×2^n (tavan 200); mazeret −25 sabit.

---

## §3. FAZ PLANI

Her faz: GÖREVLER (checkbox) → KAPI (geçilmeden sonraki faz YASAK).
Tahminler tek kişi + Cursor vibe-coding temposuna göredir.

---

### FAZ 0 — Repo & İskelet (yarım gün)

- [x] Monorepo kur: `backend/` (`niyetsen-backend/`), `mobile/`, `docs/`, kök
      `CLAUDE.md`, `NIYETSEN_MASTER_PLAN.md` — ⚠️ ne kökte ne `niyetsen-backend/`de
      git repo'su var (sadece `mobile/` git'li); henüz `git init` yapılmadı.
- [x] `backend/`: FastAPI iskeleti (`app/main.py`, `app/api/`, `app/core/`,
      `app/models/`, `app/services/`), `requirements.txt`
      (fastapi, uvicorn, google-genai, httpx, pydantic, slowapi, supabase, pyjwt)
- [x] `.env.example` dolduruldu (GEMINI_API_KEY, GEMINI_MODEL, SUPABASE_URL,
      SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET, UNSPLASH_ACCESS_KEY) — gerçek
      anahtarlar SADECE `.env`'de, `.gitignore`'da
- [x] `mobile/`: Expo (TypeScript, expo-router), `src/lib/api.ts` fetch sarmalayıcı
- [x] `GET /health` çalışır — ⚠️ mobil açılış ekranı henüz health ping ATMIYOR
      (küçük bir eksik, istenirse eklenir)
- [ ] Git init + ilk commit; her görev sonrası küçük commit kuralı başlar

**KAPI 0:** `uvicorn` ayakta, Expo Go'da uygulama açılıyor, health ping yeşil.
Ana halka (backend+mobil) çalışıyor; git init eksik.

---

### FAZ 1 — MVP HALKA: Sohbet → Görselli Plan (3–5 gün)

Amaç (docs/niyetsen-01-mvp-plan.md): "yazdım → AI bana görselli plan verdi."
Bu fazda auth/DB/puan YOK — tek cihaz, geçici state.

Backend:
- [x] `core/prompts.py`: SYSTEM_PROMPT (uygulama-promt.md §14 +
      prompts/chat_system_prompt.md TEK dosyada birleştirilmiş hali)
- [x] `core/gemini_client.py` (adı `gemini_service.py` değil ama aynı iş): chat
      çağrısı; JSON şema doğrulaması; timeout/retry, `asyncio`-uyumlu (§1.9)
- [x] `POST /chat`: niyet toplama döngüsü — kritik alanlar (şehir, ilgi, zaman)
      dolana kadar soru; `ready_for_plan` sinyali
- [x] `POST /plan/generate` + `GET /plan` (var olanı okumak için, sonradan
      eklendi) + `POST /plan/next` (partili üretim): her görev 6 kategoriden
      etiketleniyor
- [x] `services/image_service.py`: image_keyword → Unsplash URL; bulunamazsa
      kategori bazlı ikinci Unsplash sorgusu; İngilizce/somut prompt kuralı,
      güvenli içerik filtresi, deterministik ilgili sonuç, 800×600 crop ve
      fotoğrafçı attribution alanları (2026-07-10 kalite iyileştirmesi)
- [x] `services/plan_service.py`: plan JSON + görselleri birleştir, `Task.date`
      hesaplaması dahil

Mobil:
- [x] Sohbet ekranı (mesaj listesi + input + "yazıyor…" göstergesi)
- [x] Plan ekranı (gün gün görselli görev kartları, boş durum + CTA)
- [x] Hata durumları: ağ yok / Gemini hata (503) → ortak `ErrorBanner` + tekrar dene

**KAPI 1 (MVP Definition of Done):** ✅ KAPANDI (2026-07-07). "bu yıl daha sosyal
ve sağlıklı olmak istiyorum, İstanbul'dayım" yaz → AI soru sordu → sohbet akışı
Expo web üzerinden Şahin tarafından uçtan uca doğrulandı (mobil ↔ backend ↔ Gemini
gerçek zamanlı çalışıyor). Backend tarafı gerçek Gemini + Supabase ile ayrıca
smoke test'le doğrulandı.
**Not — sapmalar:**
- Fiziksel cihazda Expo Go testi App Store'un SDK 57 Expo Go onayını henüz
  vermemesi nedeniyle yapılamadı; proje SDK 54'e düşürüldü (App Store Expo Go
  uyumlu). Fiziksel cihaz testi (özellikle kanıt fotoğrafı akışı için native
  kamera) hâlâ AÇIK — bir sonraki fırsatta tekrar denenecek, UI/UX çalışmasını
  bloklamıyor.
- Unsplash API key'i `.env`'e eklendi ve doğrulandı (2026-07-07) — canlı arama
  testleri (`gym workout`, `yoga`, `reading book` vb.) gerçek Unsplash görseli
  döndürüyor. `image_service.py` yalnızca sonuç bulunamayan/anahtar eksik
  durumlarda `picsum.photos` yedeğine düşüyor.

> 🔴 DUR NOKTASI: Bu kapıyı geçince planı Belinay'a veya 2–3 arkadaşa Expo Go'dan
> göster, "vay be" tepkisi ölç. Aha anı zayıfsa plan kalitesi prompt'unu burada
> iyileştir — üstüne kat çıkmadan önce.

---

### FAZ 2 — Kalıcılık & Kimlik (3–4 gün)

- [x] Supabase projesi kur; §2'deki tablolar migration olarak yazıldı ve
      gerçek projede çalıştırıldı (`users/streaks/points/plans/tasks`, RLS açık,
      backend service_role ile bypass ediyor); `SupabaseRepository` round-trip
      smoke-test'i geçti
- [x] **Supabase kalıcılığı gerçekten aktif** (2026-07-10): `.env`'de
      `USE_SUPABASE_DB=true` + `SUPABASE_SERVICE_KEY` dolduruldu. Önceden bu
      bayrak kapalıydı — smoke test geçmiş olsa da CANLI uygulama hâlâ
      `InMemoryRepository` kullanıyordu (bug/gap olarak tespit edildi ve
      kapatıldı).
- [ ] Supabase Auth: e-posta + Google + **Apple ile Giriş** (Expo:
      `expo-apple-authentication`, `expo-auth-session`) — üç akışın mobil kodu,
      SecureStore oturumu ve Bearer JWT bağlantısı tamamlandı (2026-07-10).
      E-posta gerçek Supabase hesabıyla uçtan uca geçti. Supabase Auth ayarlarında
      Google/Apple hâlâ `external=false`; ilgili geliştirici client ID/secret
      girilip gerçek cihaz testi yapılmadan bu kutu kapanmaz.
- [x] FastAPI JWT middleware yazıldı (`get_current_user`) — JWKS tabanlı
      doğrulamaya (`SUPABASE_URL/auth/v1/.well-known/jwks.json`, RS256/ES256)
      taşındı; `SUPABASE_JWT_SECRET`/HS256 kaldırıldı. Testler sahte JWKS
      client ile doğrulanıyor. Bearer gönderildiğinde dev'de de doğrulanıyor;
      `AUTH_DISABLED=false` ayrı süreçte test edildi ve JWT'siz istek 401 döndü.
- [x] Chat geçmişi + intent DB'ye yazılır (2026-07-10): yeni `chat_msgs` +
      `intents` tabloları (migration `20260710000000_chat_and_intent.sql`);
      `/chat` client_message_id unique constraint ile idempotent yazar; retry ve
      eşzamanlı istek çift kayıt oluşturmaz. `GET /chat/session` mesajlar +
      collected intent + ready_for_plan durumunu birlikte hydrate eder;
      `/plan/generate` aktif intent'i done yapar. Gerçek Supabase'e karşı iki
      bağımsız oturum ve Gemini dahil elle doğrulandı.
- [x] Onboarding akışı: isim → doğum tarihi (burç otomatik) → bildirim saati →
      KVKK açık rıza onayı → niyet sohbeti. `kvkk_consent_at` DB'de tutuluyor.
- [x] Ayarlar ekranı: profil, bildirim saati, çıkış ve iki aşamalı
      **Hesabımı Sil**. Gerçek test hesabında DB cascade + Auth silme doğrulandı;
      Faz 3'te proofs bucket açılınca Storage temizliği aynı akışta devreye girer.

**KAPI 2:** İki farklı cihazda aynı hesapla giriş → aynı plan görünüyor.
Hesap sil → tüm veri gerçekten siliniyor (DB'de kontrol et). JWT'siz istek 401.
✅ Teknik kriterler e-posta hesabı ve iki bağımsız oturumla geçti (2026-07-10):
aynı chat + aynı plan okundu, hesap sonrası DB/Auth boş, JWT'siz istek 401.
Google/Apple sağlayıcı aktivasyonu yukarıdaki açık auth maddesi olarak kalır.

---

### FAZ 3 — Görev Motoru: Kanıt + Puan + Zincir (5–7 gün)

> ✅ Bağımsız doğrulandı (2026-07-12, Claude Code): backend test suite 86/86 yeşil
> + Şahin Expo Go'da gerçek cihazda foto→puan→rank akışını uçtan uca test etti.
> Git commit "faz3: görev ve kanıt döngüsünü tamamla" (2026-07-11) ile bu
> checkbox'lar arasındaki senkron kopukluğu bu güncellemeyle kapatıldı.

- [x] Günlük görev ekranı: bugünün görevleri, tamamla/ertele aksiyonları
      (`mobile/src/app/daily.tsx`) — Şahin tarafından Expo Go'da gerçek cihazda
      test edildi (2026-07-12).
- [x] Uygulama içi kamera (expo-camera) — galeri kapalı (§1.5): mobilde sadece
      `expo-camera` kullanılıyor, `ImagePicker`/`MediaLibrary` referansı yok —
      galeri gerçekten kapalı. Şahin gerçek cihazda kamerayla çekip gönderdi.
- [x] `POST /task/{task_id}/proof`: foto yükle (5MB limit, jpeg/png imza
      doğrulaması `proof_service.py`) → **Supabase Storage** (`proofs` bucket,
      `storage://proofs/{user_id}/...` — Railway DEĞİL, Railway sadece backend
      compute'u çalıştırıyor) → Gemini Vision güven skoru → ≥60 onay / <60
      tekrar dene (maks 3, 3.'de beyanla kabul). Kod + testler doğrulandı.
- [x] `services/scoring_service.py`: kurallar MASTER_PLAN §1.2 ile birebir
      eşleşiyor (+50 görev; sessiz kaçırma −25×2^n tavan 200; mazeret −25 sabit
      + sayaç sıfırla; 10 mazerette ×0.5; taban 0); test suite'te doğrulandı.
- [x] Mazeret akışı: `POST /task/{task_id}/excuse` + `gorev_ertele_mazeretli`
      function call — kod + test doğrulandı.
- [x] Zincir: `task_lifecycle_service.close_user_day` / `close_due_users` —
      Railway cron ile tetikleniyor; sessiz kaçırma/jeton/streak testleri geçti.
- [x] Rank ekranı: backend `overall_rank`/`rank_for` wired (`routes.py`); test
      doğrulandı.
- [x] Function calling seti (`core/tools.py`): 6 aracın tamamı (`gorev_olustur`,
      `kanit_dogrula`, `puan_guncelle`, `gorev_ertele_mazeretli`, `alarm_kur`,
      `takvime_ekle`) tanımlı; `tool_service.py` dispatch ediyor, `is_allowed()`
      kapalı liste enforcement'ı var.
- [ ] **İrade Modu** (§1.12) — KISMEN: `users.irade_modu_active` toggle alanı
      DB'de saklanıyor (`profile_service.py`) AMA açıkken İrade/Disiplin
      görevlerine OTOMATİK `alarm_kur` tetikleme mantığı henüz YOK — sadece
      genel `alarm_kur` aracı chat üzerinden (modelin kendi kararıyla)
      çağrılabiliyor. §1.12'deki otomatik linkaj eksik kalan tek madde.

**KAPI 3:** ✅ Fiilen KAPANDI (2026-07-12) — foto→puan→rank zinciri Şahin
tarafından gerçek cihazda elle doğrulandı; sessiz kaçırma/mazeret/cron akışları
backend'in 86/86 testiyle doğrulandı. Açık kalan tek madde: İrade Modu'nun
otomatik tetikleme mantığı (yukarı bakınız) — bu KAPI 3'ü bloklamıyor, Faz 3'ün
küçük bir artığı olarak kaydedildi.

---

### FAZ 4 — Bildirim + Rehber Kişiliği (3–4 gün)

> ✅ Bağımsız doğrulandı (2026-07-12, Claude Code): backend kodu + otomatik
> testler (86/86) tamam. Git commit "faz4: KVKK, bildirim ve bonus akışlarını
> tamamla" (2026-07-11) ile checkbox senkron kopukluğu kapatıldı. AÇIK KALAN:
> KAPI 4'ün elle doğrulama şartları (aşağıya bakınız) henüz yapılmadı.

- [x] Statik, responsive **Mistik Keşif** yuvası hazırlandı (2026-07-10):
      Astroloji/Fal/Tarot yalnız “Yakında · v2” ekranı + zorunlu eğlence
      disclaimer'ı; Gemini/RAG/kamera/fortune_log işlevi YOK.
- [x] Expo Push kurulumu: `push_service.py` Expo Push API (`exp.host/--/api/v2/
      push/send`) üzerinden gönderiyor — Expo bu katmanda FCM/APNs'i
      soyutluyor; kod + test doğrulandı. ⚠️ İzin akışlarının iki platformda da
      (iOS + Android 13+) gerçek cihazda elle test edilmesi HENÜZ yapılmadı.
- [x] Zamanlanmış bildirimler: `notification_service.run_due_notifications`
      (Railway cron ile tetikleniyor) — kullanıcının seçtiği saat → görev
      bildirimi; Günlük Tarot bildirimi kararlaştırıldığı gibi KAPALI. Kod +
      test doğrulandı. ⚠️ Gerçek cihazda seçilen saatte bildirimin gelip doğru
      ekranı açtığı HENÜZ elle doğrulanmadı.
- [x] Puan düşünce duygusal bildirim: `push_service.emotional_penalty_body()`
      — ton kuralına uygun ("N günlük zincirin seni bekliyor", suçlama yok).
- [x] `core/prompt_builder.py` mevcut ve kullanılıyor.
- [x] Kriz kelime filtresi (§1.8): `prompts.py` `CRISIS_KEYWORDS` +
      `contains_crisis_signal()`, `intent_service.py`'de her şeyden ÖNCE
      kontrol ediliyor; `test_chat_guardrails.py::test_crisis_message_short_
      circuits_model` geçiyor.
- [x] Scope guardrail testi: `test_chat_guardrails.py::test_math_question_
      redirects_to_user_intent` geçiyor.
- [x] **Motivasyon Bonus-Görev Hub'ı** (§1.13): `bonus_service.py` + testler
      (`test_bonus_completion_awards_ten_points_once`, `test_chat_yaptim_
      completes_active_bonus_without_model`) geçiyor.

**KAPI 4:** ⚠️ KISMEN KAPANDI — kriz mesajına güvenli yanıt kod+testle
doğrulandı. AÇIK KALAN iki elle-doğrulama maddesi: (1) bildirimin gerçek
cihazda seçilen saatte gelip doğru ekranı açtığının test edilmesi, (2) "chat,
zinciri/geçmişi bilerek konuşuyor" iddiasının 3 örnek diyalogla elle
doğrulanması. Bu ikisi yapılmadan KAPI 4 resmen KAPANMIŞ sayılmaz.

---

### FAZ 5 — Paywall + Analitik + Uyum (3–4 gün)

> 🚧 BAŞLADI (2026-07-12): backend deneme/abonelik servisi + paywall ekranı +
> PostHog HTTP iskeleti tamamlandı. RevenueCat SDK ve mağaza IAP ürünleri AÇIK.

- [x] Deneme mantığı backend'de: ilk plan → `trial_started_at` + 7 gün (`subscription_service.py`);
      süre bitince `402 paywall_required` kilidi (chat/kanıt/bonus).
- [x] `GET /me/subscription` + `POST /webhooks/revenuecat` (webhook sırrı `.env`).
- [x] Paywall ekranı mobilde (`paywall.tsx`): fiyatlar, geri yükle, koşul linkleri.
- [x] PostHog HTTP capture iskeleti (`analytics.ts`) — `EXPO_PUBLIC_POSTHOG_KEY` ile.
- [ ] RevenueCat SDK (`react-native-purchases`) + App Store / Play IAP ürünleri
      (aylık 450 TL, yıllık 3.600 TL) — Expo Go'da test edilemez, EAS build gerekir.
- [ ] Sandbox satın alma → webhook → `subscription_status=active` uçtan uca doğrulama.
- [ ] Gizlilik/Koşullar sayfaları app içinde hazır; **statik web domain** henüz yok.
- [x] Fal disclaimer metinleri app içinde (mistik yuva + legal belgeler).

**KAPI 5:** Sandbox'ta satın alma → abonelik aktif → kilitler açılıyor →
Geri Yükle çalışıyor → iptal edince kilit ekranı geliyor. PostHog'da funnel
event'leri akıyor. **Henüz KAPANMADI** — mağaza IAP + RevenueCat SDK eksik.

---

### FAZ 6 — STORE YAYINI (4–6 gün, bekleme süreleri hariç)

Hesaplar & yapı:
- [ ] Apple Developer Program ($99/yıl) + Google Play Developer ($25) hesapları
      — ONAY GÜNLER SÜREBİLİR, bu kaydı Faz 4 civarında paralel başlat
- [ ] EAS Build kurulumu (`eas.json`: development / preview / production profilleri)
- [ ] Bundle ID / package name kilitle: örn. `com.niyetsen.app`
- [ ] App ikonları (1024×1024 + adaptive icon), splash, uygulama adı, sürüm 1.0.0
- [ ] Production backend: Railway/Render'a deploy, prod .env, prod Supabase,
      Gemini ücretli katman, HTTPS, Sentry (hata izleme) ekle

Store varlıkları:
- [ ] Ekran görüntüleri: iPhone 6.7" + 6.5" + iPad (zorunluysa), Android telefon —
      5–8 ekran: onboarding, plan, görev+kanıt, rank/zincir, chat
- [ ] Store metinleri (TR): başlık, alt başlık, açıklama, anahtar kelimeler —
      "eğlence amaçlıdır" ibaresi fal'dan bahsedilen her yerde
- [ ] Yaş derecelendirme anketleri: hedef 12+ (fal içeriği "sık olmayan hafif
      olgun temalar" olarak beyan)
- [ ] Data Safety (Play) + App Privacy (Apple) formları: foto, konum(ops.),
      doğum tarihi, kimlik, analitik — DÜRÜST doldur, ret sebebi #1 burası
- [ ] Apple Review notları: **demo hesap** (e-posta+şifre) + akış açıklaması +
      "abonelik RevenueCat/IAP ile" notu

Test dağıtımı:
- [ ] TestFlight internal → kendin + Belinay + 3–5 kişi, 1 hafta gerçek kullanım
- [ ] Play Internal testing aynı grupla
- [ ] Kritik akış regresyonu: kayıt → plan → görev → kanıt → puan → paywall →
      satın alma (sandbox) → hesap silme
- [ ] Çökme oranı Sentry'de temiz; bildirimler iki platformda da geliyor

Yayın:
- [ ] Play Store'a gönder (genelde daha hızlı onay) → sonra App Store'a gönder
- [ ] Ret gelirse: sebep neyse SADECE onu düzelt, tekrar gönder (panik yok —
      ilk uygulamalarda 1–2 ret normaldir)
- [ ] Yayın günü: PostHog dashboard açık, Sentry açık, Gemini kota alarmı kur

**KAPI 6 = BİTİŞ:** Uygulama iki store'da da CANLI. İlk 50 kullanıcı hedefi başlar
(iş planı Ay 3: D1/D7 ÖLÇ — yatırımcı hikâyesi bu veridir).

---

### FAZ 7 — YAYIN SONRASI / v2 (kapsam dışı, yuva hazır)

Fal modülü (kahve/el fotoğrafı → Gemini multimodal, tarot çekimi + animasyon,
günlük burç), `services/fortune_service.py` + ikinci duygusal system prompt +
`knowledge/` RAG devreye girer (Chroma). Fal hak sayaçları
docs/niyetsen-03-algoritma.md §5'e göre. Pinterest değerlendirmesi. Leaderboard v3.
**Kural değişmedi: retention verisi gelmeden v2'ye başlama.**

---

## §4. CURSOR ÇALIŞMA PROTOKOLÜ (kesintisiz ilerleme için)

1. Her oturum başında: `CLAUDE.md` + bu dosyanın aktif fazını oku.
2. Görev sırasına sadık kal; faz atlamak, "hazır buradayken şunu da ekleyeyim"
   YASAK (scope creep = bitirmeme sebebi #1).
3. Her görev = 1 küçük commit, mesaj formatı: `faz3: proof upload + vision skoru`.
4. Her endpoint yazılınca curl/httpie ile elle test; her ekran yazılınca Expo Go'da
   gerçek cihazda test.
5. Bir KAPI kriteri geçmiyorsa: sonraki göreve GEÇME, kapıyı geçir.
6. Sır yönetimi: anahtarlar yalnız `.env`; kodda `os.environ`; `.env` gitignore'da.
7. Kararsız kaldığında: §1'deki kilitli kararlara bak; orada yoksa Şahin'e sor,
   uydurma.
8. Puan/ceza/zincir sayıları §1.2–1.3 + §2'den birebir alınır.
9. Ton kuralı her yerde: kayıp hissi + kimlik ✅, suçluluk/utandırma ❌.

## §5. RİSK RADARI (geliştirme sırasında göz önünde tut)

- Apple 4.3 (spam) riski: uygulamayı "fal uygulaması" gibi DEĞİL, "yaşam planlama +
  alışkanlık koçu" olarak konumla; fal store metinlerinde ikincil özellik.
- Gemini maliyeti: PostHog'da kullanıcı başı istek sayısını izle; context caching
  ve Flash-Lite kademesi hazırda dursun.
- Tek kişi riski: haftalık Cuma 21:00 sync'te bu dosyadaki checkbox ilerlemesi
  raporlanır — ilerleme = işaretlenen kutu, his değil.
