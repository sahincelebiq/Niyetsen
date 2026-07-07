# Niyetsen Backend — Çekirdek Beyin (v0.1)

> Bu depo Niyetsen'in **ana beynidir**: çekirdek halka (niyet sohbeti → görselli
> plan), puan/ceza/zincir motoru, kanıt doğrulama ve prompt birleştirme burada
> **çalışır halde** durur. Cursor'ın işi bunu bozmadan üzerine eklemektir.
> Yol haritası: `NIYETSEN_MASTER_PLAN.md` · Ajan kuralları: `CLAUDE.md`
> Kodun anayasası: `app/core/philosophy.py` (önce onu oku).

## Ana Felsefe (özet)
Niyetsen'in tek işi: niyeti söze, sözü günlük görevlere, görevleri kırılmayan
bir zincire çevirmek. Kayıp hissi + kimlik ✅, suçluluk ❌. En küçük halka >
mükemmel gün. Plan uydurulmaz, kullanıcının hayatından türetilir. Fal bir
ayna, kader fermanı değil. Kriz anında motivasyon durur, şefkat devreye girer.
Tam metin: `app/core/philosophy.py`.

## Hızlı Başlangıç
```bash
cd niyetsen-backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # GEMINI_API_KEY'i .env'e yaz (KODA DEĞİL)
pytest -q                   # 15 test yeşil olmalı (anahtar gerekmez)
uvicorn app.main:app --reload
# Swagger: http://127.0.0.1:8000/docs
```
Dev'de kimlik: her isteğe `X-User-Id: sahin` başlığı (AUTH_DISABLED=true iken).
Unsplash anahtarı yoksa görseller otomatik yer tutucuya düşer — halka yine çalışır.

## Uçtan Uca MVP Testi (elle)
1. `POST /chat` → `{"messages":[{"role":"user","content":"bu yıl daha sosyal ve sağlıklı olmak istiyorum, İstanbul'dayım"}]}`
2. Model soru sorar; cevapları messages'a ekleyerek tekrar gönder. `ready_for_plan: true` olunca →
3. `POST /plan/generate` → `{"collected": {...}, "duration_days": 30}` → görselli 7 günlük ilk parti döner.
4. `POST /task/{id}/proof` (foto) → onay → `GET /me/state`'te puan görünür.
5. Gün sonu: `POST /cron/close-day` → ceza + zincir işlenir.

## Mimarinin Katmanları
```
api/routes.py          HTTP kapısı: kimlik, rate limit, hata çevirisi. İş mantığı YOK.
services/              İş mantığı:
  intent_service       niyet toplama + kriz güvenlik ağı + çifte hazırlık kilidi
  plan_service         partili plan üretimi (365 günü TEK istekte üretme!)
  image_service        Unsplash → URL (v2'de Pinterest'e geçiş = sadece bu dosya)
  proof_service        Vision güven skoru + 3-deneme şefkat kuralı
  scoring_service      SAF oyun motoru — DB/HTTP/AI yok, %100 testli
core/
  prompts.py           TÜM prompt metinleri (ton değişikliği = sadece burada)
  prompt_builder.py    SYSTEM + CONTEXT(bellek) + USER — değişmez sıra
  gemini_client.py     retry/backoff/JSON-parse — model çağrısının tek kapısı
  tools.py             function calling KAPALI listesi
  philosophy.py        anayasa
models/schemas.py      API sözleşmeleri (mobil bunlara göre tip üretir)
storage/repository.py  Repository arayüzü + InMemory (v1: SupabaseRepository)
tests/test_scoring.py  oyun kurallarının SÖZLEŞMESİ — kırmızıysa kural bozuldu
```

## Cursor Genişletme Yuvaları (v1 — sırayla)
Her yuva kodda `Cursor notu` / `CURSOR YUVASI` yorumlarıyla işaretli:
1. ✅ **SupabaseRepository** (`storage/supabase_repository.py`) — aynı arayüz,
   tablolar MASTER_PLAN §2 (migration: `supabase/migrations/20260707000000_niyetsen_core_tables.sql`).
   Devreye almak için `.env`'de `SUPABASE_SERVICE_KEY` doldur + `USE_SUPABASE_DB=true`.
   Routes değişmedi.
2. ✅ **JWT doğrulama** (`api/routes.py > get_current_user`) — pyjwt +
   `SUPABASE_JWT_SECRET` (Project Settings > API > Legacy JWT Secret). Devreye
   almak için `.env`'de `AUTH_DISABLED=false`. Testler: `tests/test_auth.py`.
3. **Gün sonu zamanlayıcı** — `/cron/close-day` tek kullanıcı sürümü hazır;
   tüm kullanıcılar için APScheduler/Railway cron döngüsü yaz (kullanıcı
   timezone'unda 23:59).
4. **Chat'e function calling** — `core/tools.py` tanımları hazır;
   GenerateContentConfig'e bağla, dönen çağrıları `is_allowed` süzgecinden
   geçirip ilgili endpoint mantığına yönlendir.
5. **Foto depolama** — proof onayında dosyayı Supabase Storage'a yaz
   (kullanıcıya özel bucket; hesap silinince silinir).
6. **Bildirimler / RevenueCat / PostHog** — MASTER_PLAN Faz 4–5.
7. **RAG (v2)** — `prompt_builder.build_context(rag_chunks=...)` parametresi
   hazır; Chroma ingest v2'de.

## Dokunma (kilitli kararlar)
- Oyun sabitleri `config.py` altında: 50 puan, 25 ceza, tavan 200, taban 0,
  10 mazerette ×0.5, ayda 1 jeton. Değiştirmeden önce `tests/test_scoring.py`
  ve MASTER_PLAN §1'e bak.
- Prompt birleştirme sırası (SYSTEM → CONTEXT → USER).
- Araç listesi kapalıdır; sır `.env` dışına çıkmaz; prod'da auth kapatılamaz
  (`main.py` kilidi).
