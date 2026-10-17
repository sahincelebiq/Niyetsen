# Backend ↔ mobil API sözleşme denetimi (2026-09-06)

Kaynaklar: `niyetsen-backend/app/api/routes.py`, `app/models/schemas.py`,
mobil `src/lib/api.ts` (public `main`, 2026-09-06). Alan adları değiştirilmedi.

## KAPI özeti

| Alan | Sonuç | Not |
|---|---|---|
| Auth oturumu | **PASS** | İstemci uçları `get_current_user`. JWT'siz yalnız `/health`; cron/webhook sır ile. |
| Plan / kanıt / puan | **PASS** | `Plan`, `ProofResult`, `StateResponse` alan adları mobil tiplerle örtüşür. |
| `GET /chat/history` | **PASS** | Auth + `list[ChatMessage]`. Boş oturum `[]` (404 değil). Sorgu parametresi yok. |
| `POST /plan/next` | **PASS** | Auth + isteğe bağlı `PlanGenerateRequest`. Boş gövde / `{}` / yok → 200. Plan yoksa 404. Yanıt `Plan`. |

Hipotez doğrulandı: backend kaynak; public mobile `api.ts` history/next sarmalayıcısı yok
(paralel mobil PR bunları ekleyecek). Yeni public uç eklenmedi.

## Auth

- Prod: `ENV=prod` → `AUTH_DISABLED=false` (`main.py` kilit). Bearer = Supabase JWT
  (JWKS `RS256`/`ES256`, `aud=authenticated`, `sub` = user id).
- Dev: Bearer yoksa `X-User-Id` veya `"demo"`. **Bearer varsa JWT yine doğrulanır**
  (mobil her istekte session token gönderir).
- İstemci uçlarında JWT'siz rota yok. `/cron/*` = `X-Cron-Secret`;
  `/webhooks/revenuecat` = webhook Bearer sırrı.

## Plan / kanıt / puan

Mobil tipler backend şemalarının alt kümesi veya birebir kopyası. Ek backend
alanları (`Task.proof_id`, `ChatResponse.thread_title`) istemciyi kırmaz.

- `GET /me/state` → `StateResponse` (`points`, `ranks`, `overall_rank`, zincir
  alanları, `yesterday_silent_misses`).
- `POST /task/{id}/proof` → `ProofResult` (`approved`, `confidence`, `reason`,
  `attempt_no`, `accepted_by_declaration`, `proof_id`, `photo_url`).
- `POST /task/{id}/excuse` → `ExcuseResponse` (`message`, `events[{category,delta,reason}]`).
  Bu denetimde `response_model` kilitlendi; JSON alan adları değişmedi.
- `POST /plan/generate` premium + consent; `/plan/next` ve `/plan/ensure-today`
  mevcut planı ücretsiz uzatır (bilinçli).

Mobil `uploadTaskProof` `has_location` gönderir, lat/lng göndermez. Backend
konumu yalnız her iki koordinat varken sayar — backend davranışı doğru; istemci
düzeltmesi bu PR'ın dışı.

## `/chat/history` ve `/plan/next` (paralel mobil PR)

| Uç | İstek | Yanıt | Durum kodları |
|---|---|---|---|
| `GET /chat/history` | yok (aktif oturum) | `ChatMessage[]` | 200, 401 |
| `POST /plan/next` | isteğe bağlı `{collected, duration_days}` | `Plan` | 200, 401, 404, 503 |

- History sayfalama yok; `/chat/session` ile aynı aktif-thread listesi.
  İstemci sarmalayıcısı `/chat/session` gibi `ChatTimeoutMs` kullanmalı.
- `/plan/next` gövdesindeki `duration_days` yok sayılır (kayıtlı plan süresi).
- Rate limit: `/plan/generate` `PLAN_RATE_LIMIT` taşır; `/plan/next` ve
  `/plan/ensure-today` taşımıyor (mevcut bilinçli boşluk, bu PR'da değişmedi).

## Zaman aşımları (istemci — kod değişmedi)

| İstemci | Bütçe | Backend deneme | Retry tavanı (`GEMINI_MAX_RETRIES=3` → 4 deneme) |
|---|---|---|---|
| `ApiTimeoutMs` | 20s | — | — |
| `ChatTimeoutMs` | 75s | `GEMINI_TIMEOUT_SEC=30` | en kötü ~120s |
| `PlanTimeoutMs` | 120s | `GEMINI_PLAN_TIMEOUT_SEC=90` | en kötü ~360s |
| `ProofTimeoutMs` | 90s | `GEMINI_PROOF_TIMEOUT_SEC=45` | en kötü ~180s |

Mutlu yol (1 deneme) bütçenin içinde. Retry/fallback yolu istemciyi sessizce
aşabilir — istemci değişikliği yok; prod'da izlenmeli.

## Bilinçli dokunulmayanlar

- Yeni uç yok. Gemini araç listesi aynı.
- Public `api.ts` history/next sarmalayıcısı (paralel mobil PR).
- `/plan/next` rate limit (ensure-today ile aynı).
