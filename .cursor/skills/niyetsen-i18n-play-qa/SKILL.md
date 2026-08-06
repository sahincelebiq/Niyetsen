---
name: niyetsen-i18n-play-qa
description: Niyetsen Play Store i18n and pre-release QA. Use when adding locales, region/language pickers, preferred_language, RTL Arabic, or smoke-testing auth/onboarding/plan/daily before Play Internal testing.
---

# Niyetsen i18n + Play QA

## Supported locales (locked)

| Region | Locale | Timezone |
|--------|--------|----------|
| TR | `tr` | Europe/Istanbul |
| US | `en-US` | America/New_York |
| UK | `en-GB` | Europe/London |
| DE | `de` | Europe/Berlin |
| FR | `fr` | Europe/Paris |
| AR | `ar` | Asia/Riyadh (RTL) |

Source: `mobile/src/i18n/regions.ts` + `locales/*`. Gender API values stay Turkish strings (`kadın`/`erkek`/`belirtmek istemiyorum`); only labels translate.

## Mobile rules

1. UI strings via `useI18n().t` — do not hardcode Turkish on auth/onboarding/tabs/settings/daily/chat surfaces.
2. Persist with AsyncStorage (`niyetsen.locale`, `niyetsen.region`) through `LocaleProvider`.
3. Every API call sends `X-App-Locale` (`lib/api.ts` + `api-locale.ts`).
4. Profile `preferred_language` + `timezone` sync on onboarding save and settings region change.
5. Arabic: `I18nManager.forceRTL(true)` — warn user a reload may be needed after first RTL flip.
6. Fonts: Fraunces + Manrope only. Reanimated: never import `Easing`/`Animated` from `react-native`.

## Backend rules

1. `users.preferred_language` column (migration `20260804223000_preferred_language.sql`).
2. `build_memory_block(..., preferred_language=)` injects reply-language instruction.
3. `/chat` prefers `X-App-Locale` header, falls back to profile.
4. After schema change: add VERIFY to SQL editor file; Şahin runs VERIFY in Supabase if MCP apply unavailable.

## Pre-Play smoke (device / Expo Go)

```
- [ ] Auth: region chips visible; switch EN/DE/FR/AR then sign-in/up
- [ ] Onboarding: region first; timezone saved; gender labels localized
- [ ] Chat: reply language matches locale; plan CTA works
- [ ] Bugün: empty → extend week tasks; no crash
- [ ] Planım: generate / switch; yeni plan → sohbet
- [ ] Profil: language card + appearance light/dark only
- [ ] PRO gates: mystic/yollar/rapor (dev account OK)
- [ ] Backend: `pytest -q` green; `/health` shows gemini-3.1-pro-preview
- [ ] Mobile: `npx tsc --noEmit` zero errors
```

## Commit

- Root: `faz8: …` — mobile separate repo: `faz8-ui: …`
- Commit only when Şahin asks.
