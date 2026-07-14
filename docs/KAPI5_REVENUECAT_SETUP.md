# KAPI 5 — RevenueCat + Sandbox IAP Kurulumu

> KAPI 4 (push) tamamlandı varsayımıyla. Bu belge KAPI 5'i kapatmak için gerekenleri listeler.

## Kodda hazır olanlar

| Parça | Durum |
|-------|--------|
| `react-native-purchases` + `purchases.ts` | ✅ |
| Supabase user id = RevenueCat `app_user_id` | ✅ |
| `POST /webhooks/revenuecat` | ✅ |
| `POST /me/subscription/sync` (RC REST yedek) | ✅ |
| Paywall ekranı + SubscriptionGate | ✅ |
| PostHog funnel event'leri | ✅ |
| `scripts/verify_revenuecat_setup.py` | ✅ |

## Senden gerekenler (sırayla)

### 1. RevenueCat Dashboard
1. [app.revenuecat.com](https://app.revenuecat.com) → proje oluştur
2. **Project Settings → API keys → Secret keys** → backend için `REVENUECAT_API_KEY`
3. **Apps** → iOS (`com.niyetsen.app`) + Android (`com.niyetsen.app`) bağla → her biri için **public SDK key** (`appl_` / `goog_`)
3. **Entitlements** → `premium` oluştur
4. **Products** → mağaza ürünlerini bağla (aşağıdaki ID'ler örnek):
   - `niyetsen_monthly` — aylık ~450 TL
   - `niyetsen_yearly` — yıllık ~3.600 TL
5. **Offerings** → `default` offering, monthly + annual paketler
6. **Integrations → Webhooks**:
   - URL: `https://api-production-86f1.up.railway.app/webhooks/revenuecat`
   - Authorization: `Bearer <REVENUECAT_WEBHOOK_SECRET>` (güçlü rastgele değer)

### 2. Railway ortam değişkenleri (API servisi)
```
REVENUECAT_WEBHOOK_SECRET=<webhook bearer secret>
REVENUECAT_API_KEY=<RevenueCat secret API key — Project Settings>
REVENUECAT_ENTITLEMENT_ID=premium
```

### 3. EAS Secrets (mobil)
```
EXPO_PUBLIC_REVENUECAT_IOS_API_KEY=<RC public iOS key>
EXPO_PUBLIC_REVENUECAT_ANDROID_API_KEY=<RC public Android key>
EXPO_PUBLIC_RC_ENTITLEMENT_ID=premium
EXPO_PUBLIC_RC_MONTHLY_PACKAGE=$rc_monthly   # veya offering package id
EXPO_PUBLIC_RC_YEARLY_PACKAGE=$rc_annual
EXPO_PUBLIC_API_URL=https://api-production-86f1.up.railway.app
```

### 4. App Store Connect (sandbox)
- Subscriptions oluştur → RevenueCat'e bağla
- Sandbox tester hesabı ekle
- **Paid Applications Agreement** imzalı olmalı

### 5. Google Play Console (sandbox)
- Subscription ürünleri → RevenueCat'e bağla
- License testers ekle
- Internal testing track hazır

### 6. EAS build (Expo Go'da IAP çalışmaz)
```bash
cd mobile
eas build --profile preview --platform ios    # veya android
# TestFlight / internal APK ile sandbox satın alma
```

## KAPI 5 kapanış testi (senin cihazında)

1. Deneme süresi bitmiş veya test kullanıcısında `expired` durumu
2. Paywall açılır → sandbox satın alma
3. 5–20 sn içinde kilitler açılır (`/me/subscription/sync` + webhook)
4. Chat, kanıt, bonus çalışır
5. **Geri Yükle** → abonelik geri gelir
6. Abonelik iptal → dönem sonunda paywall

Doğrulama scripti:
```bash
cd niyetsen-backend
REVENUECAT_WEBHOOK_SECRET=... REVENUECAT_API_KEY=... \
  .venv/bin/python scripts/verify_revenuecat_setup.py
```

## PostHog funnel (beklenen event sırası)

`paywall_shown` → `subscription_started` → (kullanım) → `subscription_cancelled`

`EXPO_PUBLIC_POSTHOG_KEY` EAS secret'ta olmalı.
