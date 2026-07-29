# CLAUDE.md — Niyetsen (ajan kuralları, v2)

> Bu dosya planlama dokümanı DEĞİL. Cursor / Claude Code her oturumda bunu okur.
> Aynı içerik `.cursorrules` olarak da kullanılabilir.
> **Yol haritası ve görev sırası: `NIYETSEN_MASTER_PLAN.md` — tek gerçek kaynak.**
> Eski docs/ belgeleriyle çelişki olursa MASTER_PLAN §1 kazanır.

## Proje
Niyetsen: iOS + Android, kullanıcının 365 günlük vizyonunu sohbetle çıkaran,
görselli günlük plana çeviren, görevleri foto kanıtıyla yaptıran, yapmayınca
puan düşüren oyunlaştırılmış yaşam asistanı.

## Önce bunları oku
1. `NIYETSEN_MASTER_PLAN.md` — aktif faz + kilitli kararlar (§1) + veri modeli (§2)
   + ürün şartnamesi (rank tablosu, araçlar)
2. `docs/ARCHITECTURE.md` — mimari (backend/mobil katmanları, istek akışı)
3. `niyetsen-backend/app/core/prompts.py` — sohbet sistem promptu (gerçek kaynak;
   eski `chat_system_prompt.md` artık `docs/arsiv-planlama/`'da, güncel değil)
4. `niyetsen-backend/knowledge/` — RAG bilgi tabanı (**FAZ 7 ile AKTİF,
   2026-07-16**; Railway'e deploy için backend kökünde yaşar)
5. `docs/FAZ8_LANSMAN.md` — **AKTİF FAZ (Ağustos lansmanı, 2026-07-29)**:
   yatırımcı geri bildirimi görev listesi. (FAZ 7 arşiv: `docs/FAZ7_V2_FAL_RAG.md`)

## Stack (kilitli)
- Backend: Python 3.11+, FastAPI
- Mobil: Expo (React Native + TypeScript, expo-router)
- AI: Gemini API — `gemini-2.5-flash` (multimodal, function calling).
  FAZ 8: Railway env'den Gemini 3 ailesine geçiş; geçersiz model adında
  otomatik fallback var (`GEMINI_FALLBACK_MODEL*`). Model adı UYDURMA —
  ai.google.dev/gemini-api/docs/models'ten doğrula.
  **v1'de fine-tuning YOK.** Prod'da ücretli katman.
- DB: Supabase (Postgres + Auth + Storage). Dev'de SQLite olabilir, şema aynı.
- RAG: `rag_service.py` — Gemini embedding + in-memory kosinüs (varsayılan);
  Chroma opsiyonel yuva (requirements'a eklenmedi, Railway imaj boyutu).
- Abonelik: RevenueCat (yalnız IAP). Analitik: PostHog. Hata: Sentry.

## Güvenlik kuralları (taviz yok)
- Sırlar yalnız `.env`; kodda `os.environ`; `.env` gitignore'da; `.env.example`
  placeholder taşır.
- JWT'siz endpoint yok (health hariç) — Supabase JWT middleware her istekte.
- Foto yükleme: max 5MB, jpeg/png, sunucuda doğrula. Sadece in-app kamera.
- Rate limit: kullanıcı başına 10 chat/dk (slowapi).
- Kullanıcı mesajı asla system rolüne karışmaz; RAG içeriği etiketli CONTEXT'te.

## /chat birleştirme sırası (değişmez, `core/prompt_builder.py` tek yerde)
1. SYSTEM = `niyetsen-backend/app/core/prompts.py` (sabit)
2. CONTEXT = RAG parçaları (v2) + KULLANICI BELLEĞİ bloğu (dinamik)
3. USER = kullanıcı mesajı

## Function calling (modelin yapabildiği TEK şeyler — `core/tools.py`)
`alarm_kur`, `takvime_ekle`, `gorev_olustur`, `kanit_dogrula`, `puan_guncelle`,
`gorev_ertele_mazeretli`, `harita_yer_getir` (v2), `pinterest_gorsel_getir` (v2).
Bunların dışında araç YOK (bilet, ödeme, dosya işlemi yasak).

## Oyun kuralları (MASTER_PLAN §1–2'den, birebir uygula)
- Görev +50 puan. Sessiz kaçırma −25×2^n, **TAVAN 200**; herhangi bir görev
  tamamlanınca sayaç sıfırlanır.
- Mazeret yolu: sabit −25, katlanmaz, sayaç sıfırlanır; 10 mazerette puan ×0.5.
- **Puan tabanı 0** — negatif puan yok.
- Zincir: günde ≥1 görev = devam; gün sınırı kullanıcı timezone 23:59;
  ayda 1 Zincir Koruma Jetonu otomatik.
- Kanıt: Gemini Vision güven skoru ≥60 onay; <60 nazik tekrar (maks 3, 3.'de
  beyanla kabul).
- 6 kategori sabit: İrade, İstikrar, Disiplin, Özgüven, Sosyallik, Özsaygı.

## Çalışma disiplini
- Build sırası = MASTER_PLAN fazları. Faz atlamak ve KAPI geçmeden ilerlemek YASAK.
- Küçük commit'ler: `faz3: proof upload + vision skoru` formatı.
- Her endpoint elle test edilir; her ekran gerçek cihazda (Expo Go) test edilir.
- DB şemasını uydurma — MASTER_PLAN §2 neyse o.
- Kararsızlıkta: MASTER_PLAN §1 → yoksa Şahin'e sor. UYDURMA.

## Fal modülü (FAZ 7 — AKTİF, 2026-07-16'da Şahin onayıyla başladı)
- Fal = AYNA, kader değil. Korku satmak, tıbbi/hukuki/finansal tavsiye YASAK.
- Hak sayaçları günlük (config.FORTUNE_DAILY_RIGHTS): el 1/+2, kahve 1/+2,
  tarot 1 (ek yok), burç sınırsız. Kriz sinyalinde fal DURUR.
- İkinci system prompt: `prompts.FORTUNE_SYSTEM_PROMPT`. Yanlış fotoğraf hak yakmaz.
- Her fal yanıtında "eğlence amaçlıdır" disclaimer'ı (store uyumu).

## Yapma
- Fine-tuning (v1). Leaderboard (v3). Pinterest (v3 değerlendirmesi).
- Tanımlı araçların dışında araç çağrısı.
- Plan uydurma — her görev kullanıcının chat'te anlattığı hayattan türer.
- Suçlama/utandırma tonu: kayıp hissi + kimlik ✅ ("23 günlük zincirin seni
  bekliyor"), suçluluk ❌ ("yine yapmadın").
- localStorage (Expo'da AsyncStorage/SecureStore kullan).
- Harici ödeme linki (Apple reddi sebebi) — yalnız IAP/RevenueCat.
