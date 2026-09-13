# Supabase şema durumu (prod denetim — 2026-08-02; güncelleme 2026-09-13)

MCP ile canlı proje tarandı. API key chat’e gerekmedi (Supabase MCP bağlı).

## 2026-09-13 — Plan → Etkinlik → Bildirim → Puan hattı (agent 04)

MCP `apply_migration` ile prod’a uygulandı; migration geçmişinde kayıtlı:
`20260913131020_plan_step_events`, `20260913131242_plan_event_occurrences_fill_schedule`.
Repo dosyaları: `migrations/20260913130000_plan_step_events.sql`,
`migrations/20260913131500_plan_event_occurrences_fill_schedule.sql`; geri alma
`supabase/rollback/*_down.sql` (migrations/ dışında — `db push` onları çalıştırmasın).

| Nesne | Değişiklik |
|-------|-----------|
| `plan_events` | `task_id` (→ tasks, set null), `note`, `remind_offset_min`, `reminder_priority`, `updated_at`, `deleted_at` (soft silme). Adım başına tek aktif etkinlik: `plan_events_task_active_uniq` (partial). |
| `plan_event_occurrences` | status `pending/done/skipped/missed`; `scheduled_at` (UTC anı), `remind_at`, `reminded_at`, `snoozed_until`, `points_source` (`self`/`task`). Cron indeksi `remind_due_idx`. |
| `point_log` | `source_kind` (`task/occurrence/bonus/system`), `source_id`, `kind` (`complete/penalty/excuse/bonus/halving`). **`point_log_complete_once_uniq`**: aynı kaynak+kategori ikinci kez `complete` yazamaz (DB seviyesinde idempotent puan). 129 eski satır backfill edildi. |
| `plan_step_notes` (yeni, 18. tablo) | `(user_id, task_id)` PK, `body ≤ 2000`. RLS açık, policy yok, anon/authenticated grant yok. |
| Tetikleyiciler (projede ilk) | `point_log_fill_source_trg`: yeni kolonlar NULL gelirse `reason`’dan türetir (eski backend korumaya girer). `plan_event_occurrences_fill_trg`: `scheduled_at/remind_at` NULL ise etkinlik saati + `users.timezone`’dan UTC hesaplar; `done`’a geçişte `points_source='self'`. Backend alanı gönderirse dokunmaz. |

Kavram eşlemesi: plan adımı = `tasks` (kolon eklenmedi) · etkinlik = `plan_events` · olay = `plan_event_occurrences`.
Doğrulama: `RUN_IN_SUPABASE_SQL_EDITOR.sql` başlık 36.

## Özet

| Madde | Durum |
|-------|--------|
| 18 public tablo | ✅ hepsi var (2026-09-13: + `plan_step_notes`) |
| RLS | ✅ hepsi açık; policy yok = deny-by-default (bilinçli; backend `service_role`) |
| gender / chat_threads / fortune / idol | ✅ |
| Proof RPC’ler | ✅ claim/finish/abort + complete_bonus_offer |
| Storage | ✅ `proofs` private; `plan-images` public |
| plan-images listing policy | ✅ kaldırıldı (2026-08-02) |
| FK covering indexes | ✅ eklendi |
| Migration history (Supabase) | Kısmi — çoğu SQL Editor’dan; normalize + plan_events + plan_step_events kayıtlı |
| Auth leaked-password | ⚠️ Dashboard’da aç (HaveIBeenPwned) |
| idol_personas satır | 0 — seed ayrı (kod `knowledge/idoller.md` fallback) |

## SQL Editor disiplini (şimdiden)

1. **Yapıştırma yığını yok.** Eski Claude/Cursor DDL’lerini tekrar çalıştırma.
2. Tek doğrulama: `niyetsen-backend/supabase/migrations/RUN_IN_SUPABASE_SQL_EDITOR.sql`
3. Yeni şema değişikliği → repo’da `migrations/YYYYMMDDHHMMSS_*.sql` + MCP `apply_migration` veya Editor’da **tek** idempotent patch.
4. 05.08.2026 Pro ($25) yükseltmesi: compute/IO rahatlar; şema aynı kalır. Yükseltmeden önce bu VERIFY’ı yeşil gör.

## Bilinçli “policy yok” INFO

Advisor her tabloda “RLS on, no policy” der. Bu Niyetsen mimarisi: istemci PostgREST ile tablo okumaz; FastAPI service_role kullanır. **Tabloya rastgele `auth.uid()` policy ekleme** — yanlışlıkla veri sızdırır.

## Senin Dashboard’da 1 tık

Authentication → Providers / Password → **Leaked password protection** aç.
