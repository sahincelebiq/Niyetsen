# Ayıklanan çelişkiler (tarama 2026-09-20)

Kod/düzen değiştirilmedi. Ajan **kodu** izler; bayat doc'u ezmez.

## Skill niyeti vs kurulu paket

| İstek | Gerçek |
|---|---|
| NativeWind / Tailwind | Kurulu değil, `className` yok |
| lucide-react-native | Kurulu değil; MaterialCommunityIcons |
| Inline stil yok | ~132 `style={{}}` (çoğu dinamik tema) — temizlik sprinti değil |
| Expo docs v57 (`mobile/AGENTS.md`) | `package.json` Expo **54** |

## Model / faz

| Kaynak | İddia | Kod |
|---|---|---|
| `ARCHITECTURE.md`, bazı MASTER_PLAN satırları | Gemini 2.5-flash sohbet | `GEMINI_MODEL=gemini-3.1-pro-preview` |
| `fortune_service` dosya başı | "Gemini 2.5 Flash" | `settings.GEMINI_MODEL` |
| MASTER_PLAN §3 başlık | FAZ 5 aktif | FAZ 8 aktif |
| `niyetsen-backend/CLAUDE.md` | FAZ 7 aktif olabilir | Kök kurallar FAZ 8 |

## Araçlar / test / DB

| Kaynak | İddia | Kod |
|---|---|---|
| Eski CLAUDE araç listesi | `harita_yer_getir`, `pinterest_gorsel_getir` | `tools.py`'de yok |
| `tools.py` yorumu | "MVP'de chat araç kullanmaz" | `intent_service` GLOBAL tools bağlı |
| `AGENTS.md` | ~29 pytest | **341** |
| Çeşitli docs | 175 / 184 / 207 test | Drift; son ölçüm 341 |
| Docs | Dev SQLite | Yalnız `InMemoryRepository` |

## Ürün / fiyat / lig

| Kaynak | İddia | Güncel kilit |
|---|---|---|
| MASTER_PLAN §1.1 | 450 TL/ay | `SONRAKI_SIRA`: **150 TL/ay**, yıllık fallback 1200 |
| Play-goal kuralları | Leaderboard v3 yok | Opt-in rumuz ligi (`/league`) 2026-08-10 çekildi; **public** lig hâlâ v3 |
| Hafıza / tasarım skill | tint `#35814A`, mercan `#E06842` | `theme.ts` light: tint `#3D7A4E`, accentWarm `#D96A45` (gölge `#E06842` kalmış) |
| `theme.ts` MysticColors yorum | "şimdilik kullanılmıyor" | Mistik ekranlar `MysticColors` kullanıyor |
| `.env.example` `IMAGE_GEMINI_RATIO` | 0.5 | `config.py` default 0.15 |
| MASTER_PLAN kota | 1500 istek/gün | Preview ~250/gün — lansman blocker |

## Mobil iç tutarsızlıklar (bilinen, dokunulmadı)

- `src/constants/copy.ts` — i18n sonrası ölü Türkçe kopya (import 0).
- `boot-cache.ts` `niyetsen.boot.daily.v1` tanımlı, tüketilmiyor; Bugün `gunluk-akis.ts`.
- `src/global.css` hâlâ Inter/Spline (web kalıntı); RN font Manrope/Fraunces.
- `arkadaslar.tsx` TODO: `/league` 404 olursa kabuk kalsın, çökme.
- `subscription-gate` mistik path muaf; diğer PRO `KAPI İÇERİDE`.

## Fal hakları dil kayması

Eski kural metinleri "günlük hak" der. `config.py` (2026-08-31): ücretsiz katmanda **ömür boyu** sayaç, günlük reset yok. İsim `FORTUNE_DAILY_RIGHTS` tarihi.
