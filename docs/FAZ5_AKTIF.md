# FAZ 5 — Aktif Plan (tek açık görünüm)

> FAZ 0–4 kapandı. Bu dosya Cursor sağ panel / plan için **yalnızca aktif faz**.
> Tam arşiv: `NIYETSEN_MASTER_PLAN.md` §3.

## KAPI 5 kapanış kriteri

Sandbox satın alma → webhook/sync → `active` → kilitler açılır → Geri Yükle → iptal testi.

## Kod durumu (hazır)

- [x] Backend: trial, paywall kilidi, webhook, `/me/subscription/sync`
- [x] Mobil: paywall, RevenueCat SDK, polling, PostHog event'leri
- [x] Railway: `REVENUECAT_WEBHOOK_SECRET` + `REVENUECAT_ENTITLEMENT_ID`
- [x] EAS: `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_RC_ENTITLEMENT_ID`
- [ ] `REVENUECAT_API_KEY` (Railway)
- [ ] iOS + Android public RC key'leri (EAS)
- [ ] Mağaza IAP ürünleri + sandbox E2E

## Şahin — bu akşam sırası

Detay: `docs/KAPI5_REVENUECAT_SETUP.md`

1. RevenueCat dashboard → 3 key al → `.env` dosyalarına yapıştır
2. RevenueCat webhook → Bearer = `.env` içindeki `REVENUECAT_WEBHOOK_SECRET`
3. `python -m scripts.setup_kapi5_secrets` çalıştır
4. EAS preview build → TestFlight / internal APK
5. Sandbox satın alma testi (cihaz)

## Push bekleyen

- Mobile repo: 2 commit (`288e7ba`, `f78d471`) origin'de değil
