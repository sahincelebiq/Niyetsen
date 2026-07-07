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
- Ücretsiz: onboarding sohbeti + **ilk gerçek plan tam görünür** + **3 gün görev
  deneme** + günde 1 tarot çekimi.
- 3. günün sonunda paywall: aylık 450 TL veya yıllık 3.600 TL (aylık ~300 TL eşdeğeri).
- Gerekçe: "aha anı" yaşanmadan 450 TL ödenmez; kaybetme korkusu (3 günlük zincir +
  görünen plan) satışı yapar.

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
- Gemini çağrıları: timeout 30 sn, 2 kez exponential backoff retry, sonra kullanıcıya
  nazik hata ("Şu an yıldızlara ulaşamıyorum, birazdan tekrar dene ✨").
- Rate limit: kullanıcı başına dakikada 10 chat isteği (slowapi).
- Store yayını ÖNCESİ Gemini ücretli katmana geç (free tier 1.500 istek/gün canlıda
  yetmez). Model: `gemini-2.5-flash` (dev + prod başlangıç); pahalı işler
  (plan üretimi) için gerekirse Pro'ya yükselt.
- Prompt injection: kullanıcı mesajı asla system rolüne karışmaz; RAG içeriği
  CONTEXT bloğunda etiketli gider; model çıktısında function-call dışı araç
  denemesi reddedilir.

### 1.10 Analitik (EKSİKTİ, YATIRIMCI İÇİN KRİTİK)
- Gün 1'den itibaren **PostHog** (ücretsiz katman yeter).
- Zorunlu event'ler: `app_open`, `onboarding_complete`, `first_plan_generated`
  (AHA anı), `task_completed`, `proof_uploaded`, `paywall_shown`,
  `subscription_started`, `subscription_cancelled`, `notification_opened`.
- D1/D7/D30 retention bu event'lerden ölçülür — yatırımcı hikâyesinin tamamı bu.

### 1.11 Görsel kaynak
- MVP + v1: Unsplash (lisans temiz). Pinterest v2'ye ertelendi (API onayı yavaş +
  app içinde gösterim ToS riski — v2'de hukuki kontrol yapılacak).

---

## §2. VERİ MODELİ (Cursor bunu uydurmaz, buradan alır)

Supabase (Postgres). Dev'de lokal SQLite ile başlanabilir ama şema aynı kalır.

```
users        id (uuid, supabase auth), name, birth_date, zodiac_sign,
             timezone, notif_hour, created_at, subscription_status,
             excuse_count, freeze_tokens
intents      id, user_id, text, duration_days, status(active/done/abandoned),
             created_at
plans        id, intent_id, generated_json, created_at
tasks        id, plan_id, day_no, date, title, categories[], image_url,
             image_keyword, status(pending/done/missed_silent/missed_excused),
             proof_id?
proofs       id, task_id, photo_url, location?, confidence_score,
             attempt_no, created_at
points       user_id, category (6 sabit kategori), value  -- floor 0
point_log    id, user_id, task_id?, category, delta, reason, created_at
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
      kategori bazlı yedek görsel
- [x] `services/plan_service.py`: plan JSON + görselleri birleştir, `Task.date`
      hesaplaması dahil

Mobil:
- [x] Sohbet ekranı (mesaj listesi + input + "yazıyor…" göstergesi)
- [x] Plan ekranı (gün gün görselli görev kartları, boş durum + CTA)
- [x] Hata durumları: ağ yok / Gemini hata (503) → ortak `ErrorBanner` + tekrar dene

**KAPI 1 (MVP Definition of Done):** Expo Go'da "bu yıl daha sosyal ve sağlıklı
olmak istiyorum, İstanbul'dayım" yaz → AI 2–3 soru sorsun → 7 günlük görselli plan
ekranda görünsün. Ayrıca: Gemini kapalıyken uygulama çökmesin.
Backend tarafı gerçek Gemini + Supabase ile uçtan uca doğrulandı (bkz. §aşağıdaki
smoke test). **Fiziksel cihazda Expo Go üzerinden son onay henüz Şahin tarafından
yapılmadı — KAPI 1 bu adım tamamlanınca resmen kapanır.**

> 🔴 DUR NOKTASI: Bu kapıyı geçince planı Belinay'a veya 2–3 arkadaşa Expo Go'dan
> göster, "vay be" tepkisi ölç. Aha anı zayıfsa plan kalitesi prompt'unu burada
> iyileştir — üstüne kat çıkmadan önce.

---

### FAZ 2 — Kalıcılık & Kimlik (3–4 gün)

- [x] Supabase projesi kur; §2'deki tablolar migration olarak yazıldı ve
      gerçek projede çalıştırıldı (`users/streaks/points/plans/tasks`, RLS açık,
      backend service_role ile bypass ediyor); `SupabaseRepository` round-trip
      smoke-test'i geçti
- [ ] Supabase Auth: e-posta + Google + **Apple ile Giriş** (Expo:
      `expo-apple-authentication`, `expo-auth-session`) — mobil hâlâ anonim
      `X-User-Id` (AsyncStorage) kullanıyor, gerçek login YOK
- [x] FastAPI JWT middleware yazıldı (`get_current_user`) — JWKS tabanlı
      doğrulamaya (`SUPABASE_URL/auth/v1/.well-known/jwks.json`, RS256/ES256)
      taşındı; `SUPABASE_JWT_SECRET`/HS256 kaldırıldı. Testler sahte JWKS
      client ile 29/29 geçiyor. `AUTH_DISABLED=true` kaldığı sürece devrede
      değil — Apple/Google login akışı bağlanınca sadece bunu `false` yapmak
      yeterli.
- [ ] Chat geçmişi + intent DB'ye yazılır (plan/görevler/puan zaten Supabase'de
      kalıcı ama sohbet mesajları hâlâ sadece mobil local state'te — uygulama
      kapanınca sohbet geçmişi kaybolur, plan kaybolmaz)
- [ ] Onboarding akışı: isim → doğum tarihi (burç otomatik) → bildirim saati →
      KVKK açık rıza onayı → niyet sohbeti
- [ ] Ayarlar ekranı: profil, bildirim saati, **Hesabımı Sil** (tam silme:
      DB + Storage + auth kaydı)

**KAPI 2:** İki farklı cihazda aynı hesapla giriş → aynı plan görünüyor.
Hesap sil → tüm veri gerçekten siliniyor (DB'de kontrol et). JWT'siz istek 401.

---

### FAZ 3 — Görev Motoru: Kanıt + Puan + Zincir (5–7 gün)

- [ ] Günlük görev ekranı: bugünün görevleri, tamamla/ertele aksiyonları
- [ ] Uygulama içi kamera (expo-camera) — galeri kapalı (§1.5)
- [ ] `POST /task/proof`: foto yükle (5MB limit) → Supabase Storage →
      Gemini Vision güven skoru → ≥60 onay / <60 tekrar dene (maks 3)
- [ ] `services/scoring_service.py`: +50 görev; sessiz kaçırma −25×2^n tavan 200;
      mazeret yolu −25 sabit + sayaç sıfırla; 10 mazerette ×0.5; **taban 0**;
      her hareket `point_log`'a
- [ ] Mazeret akışı: chat'te "bugün yapamayacağım çünkü…" → model mazereti tanır →
      `gorev_ertele_mazeretli` function call
- [ ] Zincir: günlük iş (§1.3) — gün sonu cron (backend scheduler / Railway cron):
      tamamlanmayanları işaretle, cezaları uygula, jeton kontrolü, streak güncelle
- [ ] Rank ekranı: 6 kategori + kademe (Bronz III → Usta) + genel rütbe + zincir
      sayacı büyük ve görünür
- [ ] Function calling seti (`core/tools.py`): `gorev_olustur`, `kanit_dogrula`,
      `puan_guncelle`, `gorev_ertele_mazeretli`, `alarm_kur`, `takvime_ekle`
      (alarm/takvim mobilde expo-calendar + local notification ile)

**KAPI 3:** Bir görevi fotola → puan işlendi → rank ekranında görünüyor.
Bir görevi sessiz kaçır → gece cron'u cezayı katlayarak işledi (log'da doğrula).
Mazeret yaz → sabit 25 kesildi, katlanma sıfırlandı. Puan 0'ın altına inmiyor.

---

### FAZ 4 — Bildirim + Rehber Kişiliği (3–4 gün)

- [ ] Expo Push + FCM kurulumu; izin akışları (iOS + Android 13+)
- [ ] Zamanlanmış bildirimler: kullanıcının seçtiği saat → görev bildirimi;
      +1 dk → Günlük Tarot bildirimi (v2'ye kadar tarot bildirimi "yakında" ekranına
      gider — YA DA bu bildirimi v2'ye kadar kapalı tut, karar: KAPALI TUT)
- [ ] Puan düşünce duygusal bildirim — ton: kayıp hissi + kimlik, ASLA suçlama
      ("23 günlük zincirin seni bekliyor" ✅ / "yine yapmadın" ❌)
- [ ] `core/prompt_builder.py`: SYSTEM + CONTEXT (KULLANICI BELLEĞİ bloğu: niyet,
      zincir, son görevler, rank, burç, son ruh hali) + USER — README.md'deki
      şablonla birebir
- [ ] Kriz kelime filtresi (§1.8): tetiklenince güvenli mod yanıtı
- [ ] Scope guardrail testi: matematik sorusu → model reddedip niyete döner

**KAPI 4:** Bildirim seçilen saatte geliyor, tıklayınca uygulama doğru ekranda
açılıyor. Chat, kullanıcının zincirini ve geçmişini bilerek konuşuyor
(3 örnek diyalogla elle doğrula). Kriz mesajına güvenli yanıt veriyor.

---

### FAZ 5 — Paywall + Analitik + Uyum (3–4 gün)

- [ ] RevenueCat kur: aylık 450 TL + yıllık 3.600 TL ürünleri (App Store Connect +
      Play Console'da IAP ürünleri oluştur)
- [ ] Deneme mantığı: ilk plan + 3 gün görev ücretsiz (§1.1) → 3. gün sonunda
      paywall; deneme durumu backend'de (`users.subscription_status`)
- [ ] Paywall ekranı: değer anlatımı ("planın hazır, zincirin başladı — devam et"),
      fiyatlar, Geri Yükle butonu, koşul linkleri (§1.7)
- [ ] RevenueCat webhook → `subscription_status` güncelle; abonelik bitince
      nazik kilit ekranı (veri silinmez, erişim kilitlenir)
- [ ] PostHog entegrasyonu + §1.10'daki tüm event'ler
- [ ] Gizlilik Politikası + Kullanım Koşulları sayfaları yayında (domain al)
- [ ] Fal disclaimer metinleri hazır (v2 modülü için şimdiden — store açıklamasında
      da kullanılacak)

**KAPI 5:** Sandbox'ta satın alma → abonelik aktif → kilitler açılıyor →
Geri Yükle çalışıyor → iptal edince kilit ekranı geliyor. PostHog'da funnel
event'leri akıyor.

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
