# Supabase şema durumu (prod denetim — 2026-08-02)

MCP ile canlı proje tarandı. API key chat’e gerekmedi (Supabase MCP bağlı).

## Özet

| Madde | Durum |
|-------|--------|
| 17 public tablo | ✅ hepsi var |
| RLS | ✅ hepsi açık; policy yok = deny-by-default (bilinçli; backend `service_role`) |
| gender / chat_threads / fortune / idol | ✅ |
| Proof RPC’ler | ✅ claim/finish/abort + complete_bonus_offer |
| Storage | ✅ `proofs` private; `plan-images` public |
| plan-images listing policy | ✅ kaldırıldı (2026-08-02) |
| FK covering indexes | ✅ eklendi |
| Migration history (Supabase) | Kısmi — çoğu SQL Editor’dan; yeni normalize migration kayıtlı |
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
