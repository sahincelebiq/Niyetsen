# Plan-içi ajan + etkinlik (dilim 1) — tasarım

Tarih: 2026-09-10. Kaynak: `gemini-code-1789027060551.json` + Şahin kilitleri.
Sonraki dilimler (ayrı): ajanda notları, nudge motoru, Bugün stat rozeti UI, i18n.

## Kilitler

- 365 kök plan (`POST /plan/generate`) değişmez. Ücretsiz = 1 kök plan.
- İki düğme: **Etkinlik ekle** (bu dilim) ve **Yeni niyet** (mevcut sohbet).
- Tek seferlik ve tekrarlayan paket = `plan_events` (Unsplash yok).
- Tekrar: `none` | `daily` | `weekdays` | `weekly` + `byweekday[]`, saat, bitiş.
- 365 görev: foto kanıt. Etkinlik: fotosuz **Yaptım** → +50, kategori, zincir kurtarabilir.
- Etkinlik kaçınca ceza yok; sessiz kaçırma yalnız 365 `tasks`.
- Kategori: başlıktan otomatik, form/ajan düzeltir.
- Plan-içi sohbet `chat_threads.kind=plan_agent`; `/chat/threads` listesine girmez.
- Yeni araç `etkinlik_olustur` (Şahin 2026-09-10). Global `/chat` bu aracı görmez.

## Veri

`plan_events` + `plan_event_occurrences` (event_id+date unique). `tasks` aynı.
`plans.id` text FK. RLS açık, anon policy yok (service_role).

## API

- `POST /plan/{plan_id}/events` — form
- `GET /plan/{plan_id}/events`
- `POST /plan/events/{occurrence_id}/complete` — beyan
- `GET /tasks/daily` → `events: DailyEventItem[]` (eski `items` durur)
- `POST /plan/{plan_id}/chat` + `GET /plan/{plan_id}/chat/history`
- `etkinlik_olustur` yalnız plan-içi dispatch (`plan_id` zorunlu)

## Skor / rapor

`complete_task` +50. `close_user_day`: pending occurrence cezalanmaz.
`any_completed` = 365 done **veya** occurrence done.
Rapor: `point_log` reason `etkinlik tamamlandı` (occurrence_id = task_id).

## Mobil (ayrı repo, dilim 1b)

Plan detay: gömülü sohbet + Etkinlik ekle formu. Bugün: `events` → Yaptım, kamera yok.
Nudge (dilim 3): `scheduled_time` şimdiden kayıtlı.
