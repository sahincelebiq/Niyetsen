---
name: niyetsen-core
description: Niyetsen ürün hafızası ve kod gerçeği — kimlik, kilitli oyun kuralları, gerçek stack (Expo 54 + FastAPI + Gemini 3.1, NativeWind/Lucide YOK), tuzaklar, sprint sırası. Niyetsen, mobil, backend, sohbet, plan, kanıt, zincir, fal/mistik, paywall, Play Store veya "Niyetsen'i hatırla" işlerinde kullan. Yeni ekran, API, prompt, migration veya UI değişikliğinden önce oku.
---

# Niyetsen Core

İki ayrı git deposu: kök `Niyetsen` (backend + docs) ve `Niyetsen-mobile`.
Yol öneki: kökte `mobile/` + `niyetsen-backend/`; mobil repoda `src/` + kardeş `../niyetsen-backend/`.

Kararsızlıkta sıra: **kod** → `NIYETSEN_MASTER_PLAN.md` §1 → bu skill → Şahin.
Eski doc ile kod çelişirse **kod kazanır**. Çelişki listesi: [ayiklanan-celiskiler.md](ayiklanan-celiskiler.md).
Dosya haritası: [codebase-map.md](codebase-map.md).

---

## Core Principles
- Stack: Expo (React Native), TypeScript, Supabase, NativeWind/Tailwind.
- Always use functional components with strictly typed interfaces (no 'any').
- Implement clean, responsive, and platform-native UI/UX.

## Design & UI Guidelines
- Modern, clean, and minimalist design language: generous whitespace, subtle rounded borders (rounded-2xl/3xl), and clean typography.
- Never use inline raw styles; prefer NativeWind utility classes or dedicated StyleSheet objects.
- Ensure minimum touch target size of 44x44 points for all interactive buttons.
- Optimize images using fast loading patterns; use Lucide-react-native or Expo Vector Icons consistently.

## Code Quality & Architecture
- Follow the single-responsibility principle: separate business logic into custom hooks (`/hooks`) and UI into presentational components (`/components`).
- Error Handling: Handle errors at the beginning of functions with early returns; always catch Supabase query exceptions gracefully.
- State Management: Minimize unnecessary re-renders with React.memo or useMemo where derived state is involved.

---

## Bu ilkelerin Niyetsen kodundaki karşılığı

Yukarıdaki İngilizce niyet korunur; **kurulum ve kütüphane seçimi kod gerçeğine uyar**. NativeWind / Lucide **ekleme**.

| Niyet | Kod gerçeği (2026-09 tarama) |
|---|---|
| Expo + TS + Supabase | Evet. Mobil Expo **SDK 54** (`expo ~54.0.36`, RN 0.81.5). `AGENTS.md` v57 docs linki **yanlış** — yazarken [Expo v54](https://docs.expo.dev/versions/v54.0.0/) oku. |
| NativeWind / Tailwind / `className` | **YOK.** `package.json`'da nativewind/tailwind yok. Stil: `theme.ts` token + `StyleSheet.create` + `useTheme()`. |
| Lucide | **YOK.** İkon: `@expo/vector-icons` `MaterialCommunityIcons` + tab'larda `VectorIcon`. |
| Inline stil yasak | Hedef: yeni UI'da ham hex/`padding: 12` yığınlama. Mevcut kodda `style={{}}` var (dinamik tema/inset); silme turu yapma. Yeni kod: StyleSheet + token. |
| `rounded-2xl/3xl` | NativeWind sınıfı yok. Eşdeğer: `Radii` (`small` 10, `medium` 16, `large` 18, `pill` 999). |
| `no any` | `strict: true`; `src/` içinde `: any` / `as any` ≈ 0. Koru. |
| hooks / components | `src/hooks/`, `src/components/`, iş kuralı `src/lib/`. Backend: `services/` + `routes.py`. |
| Supabase hata | Mobil auth `lib/supabase.ts` (SecureStore). Veri **istemciden Postgres'e gitmez** — JWT ile FastAPI, sunucu `service_role`. Catch: `lib/api.ts` + ekranda error-banner. |
| 44pt dokunma | Zorunlu. `minHeight`/`minWidth` 44 veya `hitSlop`. |
| Görsel | `expo-image`; boyut + `resizeMode`; layout shift yok. |

UI işinde ayrıca `niyetsen-tasarim` skill'ini uygula.

---

## Ürün (tek cümle)

Niyetsen: sohbetle 365 günlük niyeti görsel plana çeviren, görevleri **uygulama içi kamera** kanıtıyla doğrulayan, yapmayınca puan düşüren (taban 0), zincir büyüten oyunlaştırılmış yaşam asistanı. Fal = ayna, kader değil. Ödeme yalnız IAP/RevenueCat.

Paket: `com.niyetsenai`. Mobil sürüm `1.1.4`. API `1.1.1`. Dev: `kutluadalarr7@gmail.com`.

---

## Sözlük

| Terim | Anlam |
|---|---|
| **Zincir** | Streak. ≥1 görev (veya fotosuz etkinlik) = gün sayılır. Sınır: kullanıcı TZ 23:59. Ayda 1 Zincir Koruma Jetonu. 12 hayvanlı evrim. |
| **Mazeret** | `missed_excused` −25 sabit, katlanmaz. **Sessiz kaçırma** −25×2ⁿ, tavan 200. |
| **KAPI** | Faz çıkış kriteri. Geçmeden sonraki işe başlama. **KAPI İÇERİDE**: PRO ekran görünür + kilit önizleme; `replace('/paywall')` ile dışarı atma (fal muaf). |
| **İdol / Felsefe Yolları** | Kamuya açık kişiden ilham; paket adı felsefe. Kişi adı yalnız disclaimer'da. |
| **Wrapped / Rapor** | `/me/recap`. Yalnız kazanım; kaçırılan listelenmez. |
| **İlkbahar** | UI v3 paleti. Sonbahar pastel geri gelmez. Token: `src/constants/theme.ts` — hex'i oradan al, dokümandaki eski `#35814A` ezmesin. |

---

## Kilitli oyun kuralları (`config.py` — uydurma)

- 6 kategori: İrade, İstikrar, Disiplin, Özgüven, Sosyallik, Özsaygı.
- Görev +50 / kategori etiketi. Bonus +10. Puan tabanı 0.
- Kanıt: JPEG/PNG ≤5MB, Vision ≥60, maks 3 deneme, 3.'de beyan. Anlamsal eşleşme zorunlu (su ≠ meyve).
- Ücretsiz = 1 plan; 2. plan `subscription.status == "active"` (trial yetmez).
- Sohbet ücretsiz sınırsız. Plan/kanıt/bonus/İdol/uzatılmış rapor PRO.
- Cinsiyet string birebir: `kadın` / `erkek` / `belirtmek istemiyorum`.
- Fal ücretsiz ömür boyu: el 1, kahve 1, tarot 1, mistik sohbet 5; burç sınırsız. PRO (`active`) sınırsız. Krizde fal durur. Her yanıtta eğlence disclaimer.
- Araçlar yalnız `core/tools.py`: `gorev_olustur`, `kanit_dogrula`, `puan_guncelle` (sunucu reddeder), `gorev_ertele_mazeretli`, `alarm_kur`, `takvime_ekle`, `etkinlik_olustur` (yalnız plan ajanı). `harita_yer_getir` / `pinterest_*` **kodda yok**.
- Prompt sırası (`prompt_builder.py`): SYSTEM → CONTEXT (RAG + KULLANICI BELLEĞİ) → USER. Kullanıcı metni system'e karışmaz.
- Model: `gemini-3.1-pro-preview` (sohbet+plan); fallback `gemini-2.5-flash` / `2.5-pro`. İsim uydurma. Gemini 3'te `thinking_budget=0` geçersiz → `thinking_level="low"`.
- v1 yok: fine-tune, public leaderboard, harici ödeme linki, `localStorage`.

---

## Stack (kod)

**Mobil:** Expo Router `src/app/`, 5 tab (Sohbet / Bugün / Planım / Zincir / Profil). Font: Manrope + Fraunces. Tipografi kilit: title 32 / screenTitle 22 / subtitle 18. Reanimated 4; `Easing`/`Animated` **asla** `react-native`'den. `count-up-text.tsx` bilerek RAF. i18n: `tr` `en-US` `en-GB` `de` `fr` `ar`.

**Backend:** FastAPI, tek router `app/api/routes.py`, pytest **341**. Prod: Railway `api` + `cron`. DB: Supabase Postgres; test: `InMemoryRepository` (SQLite yok). JWT: imzalı `email` claim (metadata değil).

**Vitrin site:** `website/` — uygulama paleti değil (terracotta); IAP linki yok.

---

## Tuzaklar (canlıda yaşandı)

1. Reanimated Easing — eslint kuralını kaldırma.
2. `plans.id` **TEXT**, UUID değil → FK `plan_id text`.
3. `chat_threads` degrade: thread hatası sohbeti/plan geçişini düşürmez.
4. Migration otomatik değil; VERIFY: `RUN_IN_SUPABASE_SQL_EDITOR.sql`.
5. Cron: `railway.cron.toml`; uvicorn açılırsa 5 dk SIGKILL.
6. Railway: GitHub push deploy tetiklemez. `api` **repo kökünden** `railway up`; `niyetsen-backend/` içinden yol çiftlenir. Staged destructive patch'e `accept-deploy` yok.
7. zsh `path=` PATH'i ezer.
8. EAS: `EXPO_PUBLIC_SUPABASE_*` yoksa app ölü açılır.
9. `CLOSED_TEST_EMAILS` boş = kısa devre yok.
10. Klavye: `KeyboardAwareView` + ölçüm; Dimensions tahmini yasak.

---

## Sprint (Şahin “devam et” demeden atlama)

Kuyruk: `docs/SONRAKI_SIRA.md`. Hedef: `docs/PLAYSTORE_GOAL.md`. B1–B9 kapanmadan “hazır” denmez.

Sıra: Alpha yayın → RC/Play IAP (150 TL/ay kilit) → paywall doğrula → rapor → mistik → ana ajan → örüntü (ConvNet yok) → MiniMax yalnız aday.

Commit yalnız Şahin isteyince. Kök: `faz8: …` / mobil: `faz8-ui: …`.

Doğrulama: backend `pytest -q` yeşil; mobil `npx tsc --noEmit` 0 hata; ekran Expo Go gerçek cihaz.

---

## UI iskeleti (yeni ekran)

`ThemedText` / `ThemedView` / `screen-scaffold` / `SurfaceCard`. Hex hardcode yok. Kullanıcı metni Türkçe (`useI18n().t`); "task" yazma. 3 durum: yükleniyor / boş / hata. iPhone SE (375) taşmasın. Web-boyu başlık (28pt+) yasak.

Detay: skill `niyetsen-tasarim`. i18n/Play QA: `niyetsen-i18n-play-qa`. Mağaza vitrin: `niyetsen-play-store-listing`.
