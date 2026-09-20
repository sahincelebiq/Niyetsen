# Niyetsen dosya haritası

Kök yollar. Mobil repoda `mobile/` önekini düş, backend için `../niyetsen-backend/` kullan.

## Kök (Niyetsen)

| Dosya | Rol |
|---|---|
| `NIYETSEN_MASTER_PLAN.md` | Ürün şartnamesi §1–2; bazı model/fiyat satırları bayat — kodla doğrula |
| `CLAUDE.md` | Ajan kuralları |
| `AGENTS.md` | Cloud VM notları; **pytest 29 yazıyor — yanlış, 341** |
| `docs/FAZ8_LANSMAN.md` | Aktif faz görev + KAPI |
| `docs/PLAYSTORE_GOAL.md` | Aktif sprint, B1–B9 |
| `docs/SONRAKI_SIRA.md` | Kilitli kuyruk |
| `docs/UI_V3_ILKBAHAR.md` | Ekran turu + mikro-etkileşim |
| `docs/ARCHITECTURE.md` | Katmanlar; Gemini 2.5 satırları bayat |
| `docs/REPO_MAP.md` | Dizin + uç grupları |
| `.cursor/rules/niyetsen-hafiza.mdc` | Damıtılmış hafıza |
| `website/` | niyetsen.com vitrin |

## Backend `niyetsen-backend/`

| Dosya | Rol |
|---|---|
| `app/main.py` | FastAPI; prod kilitleri |
| `app/config.py` | Env + oyun sabitleri |
| `app/api/routes.py` | Tüm HTTP uçları |
| `app/core/prompts.py` | SYSTEM / FORTUNE / PROOF |
| `app/core/tools.py` | Kapalı araç listesi |
| `app/core/prompt_builder.py` | Bellek + CONTEXT |
| `app/core/gemini_client.py` | thinking_level / fallback |
| `app/services/scoring_service.py` | Puan/zincir (I/O yok) |
| `app/services/intent_service.py` | `/chat` |
| `app/services/plan_service.py` | Plan üretimi |
| `app/services/plan_agent_service.py` | Plan-içi ajan |
| `app/services/proof_service.py` | Vision kanıt |
| `app/services/fortune_service.py` | Fal |
| `app/services/event_service.py` | Fotosuz etkinlik |
| `app/storage/supabase_repository.py` | Prod DB |
| `knowledge/` | RAG (Docker COPY) |
| `supabase/migrations/` | DDL; Editor'a yalnız VERIFY |
| `tests/conftest.py` | InMemory + AUTH_DISABLED |
| `railway.api.toml` / `railway.cron.toml` | Servis config |

Uç özeti: JWT zorunlu (`/health` hariç). `/chat`, `/plan/*`, `/task/{id}/proof|excuse`, `/tasks/daily`, `/me/state|recap|profile|subscription`, `/fortune/*`, `/paths/*`, `/league*`, `/cron/*` (`X-Cron-Secret`).

## Mobil `mobile/`

| Dosya | Rol |
|---|---|
| `src/constants/theme.ts` | İlkbahar + MysticColors + Spacing/Radii/Motion |
| `src/constants/zodiac.ts` | Burç helper |
| `src/components/themed-text.tsx` | Tipografi kilit |
| `src/components/screen-scaffold.tsx` | Ekran iskeleti |
| `src/app/_layout.tsx` | Provider zinciri |
| `src/app/(tabs)/index.tsx` | Sohbet |
| `src/app/(tabs)/daily.tsx` | Bugün |
| `src/app/(tabs)/explore.tsx` | Planım |
| `src/app/(tabs)/rank.tsx` | Zincir |
| `src/app/(tabs)/settings.tsx` | Profil |
| `src/app/paywall.tsx` | İlkbahar paywall |
| `src/app/rapor.tsx` | KAPI İÇERİDE örnek |
| `src/app/mystic.tsx` | Fal hub |
| `src/lib/api.ts` | Backend istemci |
| `src/lib/supabase.ts` | Auth session |
| `src/lib/purchases.ts` | RevenueCat |
| `src/lib/gunluk-akis.ts` | Bugün SWR cache |
| `src/lib/boot-cache.ts` | Profil/abonelik açılış cache |
| `src/i18n/` | 6 dil |
| `eslint.config.js` | Easing yasağı |

Tab ikonları: `src/components/app-tabs.tsx`.
