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
2. `docs/uygulama-promt.md` — ürün şartnamesi (rank tablosu, araçlar)
3. `docs/niyetsen-02-mimari.md` — mimari
4. `prompts/chat_system_prompt.md` — sohbet sistem promptu
5. `knowledge/` — RAG bilgi tabanı (V2 fal modülü için, ŞİMDİ DEĞİL)

## Stack (kilitli)
- Backend: Python 3.11+, FastAPI
- Mobil: Expo (React Native + TypeScript, expo-router)
- AI: Gemini API — `gemini-2.5-flash` (multimodal, function calling).
  **v1'de fine-tuning YOK.** Prod'da ücretli katman.
- DB: Supabase (Postgres + Auth + Storage). Dev'de SQLite olabilir, şema aynı.
- Vektör DB: Chroma (local) — sadece V2 fal modülünde devreye girer.
- Abonelik: RevenueCat (yalnız IAP). Analitik: PostHog. Hata: Sentry.

## Güvenlik kuralları (taviz yok)
- Sırlar yalnız `.env`; kodda `os.environ`; `.env` gitignore'da; `.env.example`
  placeholder taşır.
- JWT'siz endpoint yok (health hariç) — Supabase JWT middleware her istekte.
- Foto yükleme: max 5MB, jpeg/png, sunucuda doğrula. Sadece in-app kamera.
- Rate limit: kullanıcı başına 10 chat/dk (slowapi).
- Kullanıcı mesajı asla system rolüne karışmaz; RAG içeriği etiketli CONTEXT'te.

## /chat birleştirme sırası (değişmez, `core/prompt_builder.py` tek yerde)
1. SYSTEM = `prompts/chat_system_prompt.md` (sabit)
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

## Yapma
- Fine-tuning (v1). Fal modülü / RAG (v2'den önce). Leaderboard (v3).
- Tanımlı araçların dışında araç çağrısı.
- Plan uydurma — her görev kullanıcının chat'te anlattığı hayattan türer.
- Suçlama/utandırma tonu: kayıp hissi + kimlik ✅ ("23 günlük zincirin seni
  bekliyor"), suçluluk ❌ ("yine yapmadın").
- localStorage (Expo'da AsyncStorage/SecureStore kullan).
- Harici ödeme linki (Apple reddi sebebi) — yalnız IAP/RevenueCat.
