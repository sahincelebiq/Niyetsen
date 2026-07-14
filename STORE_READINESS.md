# Niyetsen — Store Yayın Hazırlığı (FAZ 6)

> Bu belge **yayınlama** değil, mağazaya göndermeye hazır yapıyı tanımlar.
> FAZ 7 (fal/RAG) kapsam dışıdır.

## Tamamlanan teknik yapı

| Alan | Durum | Not |
|------|-------|-----|
| Backend prod (Railway) | ✅ | `https://api-production-86f1.up.railway.app` |
| Supabase (Auth + DB + Storage) | ✅ | Prod migration'lar uygulanmalı |
| Cron (gün sonu + bildirim) | ✅ | `CRON_SECRET` + `API_BASE_URL` eşleşmeli |
| Gemini 2.5 Flash / Pro | ✅ | Plan=Pro, chat/kanıt=Flash |
| RevenueCat webhook | ✅ | `REVENUECAT_WEBHOOK_SECRET` prod zorunlu |
| Mobil bundle ID | ✅ | `com.niyetsen.app` |
| EAS profilleri | ✅ | `development` / `preview` / `production` |
| PostHog event iskeleti | ✅ | `EXPO_PUBLIC_POSTHOG_KEY` ile |
| Sentry iskeleti | ✅ | `SENTRY_DSN` / `EXPO_PUBLIC_SENTRY_DSN` ile |
| Uygulama içi legal | ✅ | Gizlilik, KVKK, Koşullar, rıza |

## Şahin'in elle yapması gerekenler (kod dışı)

### 1. Apple Developer + Google Play Console
- [ ] Apple Developer Program ($99/yıl) onayı
- [ ] Google Play Developer ($25) hesabı
- [ ] App Store Connect + Play Console'da `com.niyetsen.app` uygulaması oluştur

### 2. RevenueCat + IAP ürünleri
- [ ] RevenueCat projesi: iOS + Android app bağla
- [ ] Entitlement: `premium`
- [ ] Ürünler: aylık ~450 TL, yıllık ~3.600 TL (mağaza fiyatlandırması)
- [ ] Webhook URL: `https://api-production-86f1.up.railway.app/webhooks/revenuecat`
- [ ] Sandbox satın alma → `subscription_status=active` doğrula

### 3. Supabase OAuth
- [ ] Google + Apple provider'ları Supabase dashboard'da aktif et
- [ ] Redirect URL'leri Expo scheme ile eşleştir (`niyetsen://`)
- [ ] Gerçek cihazda OAuth giriş testi

### 4. EAS production build
```bash
cd mobile
eas secret:create --scope project --name EXPO_PUBLIC_API_URL --value https://api-production-86f1.up.railway.app
eas secret:create --scope project --name EXPO_PUBLIC_REVENUECAT_IOS_API_KEY --value <rc-ios>
eas secret:create --scope project --name EXPO_PUBLIC_REVENUECAT_ANDROID_API_KEY --value <rc-android>
eas build --profile production --platform all
```

### 5. Store varlıkları
- [ ] 1024×1024 ikon (mevcut `assets/images/icon.png` kontrol)
- [ ] Ekran görüntüleri: onboarding, plan, görev+kanıt, rank, chat (5–8 adet)
- [ ] TR store metinleri + yaş derecelendirme anketi
- [ ] App Privacy (Apple) + Data Safety (Play) formları — dürüst doldur
- [ ] Apple Review Notes: demo hesap + akış açıklaması

### 6. Test dağıtımı (yayın öncesi)
- [ ] TestFlight internal (1 hafta gerçek kullanım)
- [ ] Play Internal testing
- [ ] Regresyon: kayıt → plan → görev → kanıt → puan → paywall → sandbox IAP → hesap silme
- [ ] Push: iOS + Android 13+ gerçek cihazda saat testi

## Yayınlama (henüz yapma)

Aşağıdaki adımlar yapı hazır olduktan sonra:
1. Play Internal → Production track
2. TestFlight → App Store Review
3. Ret gelirse yalnız belirtilen maddeyi düzelt

## Ortam değişkenleri kontrol listesi

### Railway API (`ENV=prod`)
- `AUTH_DISABLED=false`
- `USE_SUPABASE_DB=true`
- `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `CRON_SECRET`, `REVENUECAT_WEBHOOK_SECRET`
- `CORS_ALLOWED_ORIGINS` (web istemcisi varsa)
- `SENTRY_DSN` (opsiyonel)

### Railway Cron
- `API_BASE_URL=https://api-production-86f1.up.railway.app`
- `CRON_SECRET` (API ile aynı)

### Mobil EAS Secrets
- `EXPO_PUBLIC_API_URL`
- `EXPO_PUBLIC_REVENUECAT_*`
- `EXPO_PUBLIC_POSTHOG_KEY` (opsiyonel)
- `EXPO_PUBLIC_SENTRY_DSN` (opsiyonel)

## KAPI durumu

| KAPI | Durum |
|------|-------|
| KAPI 3 (görev/kanıt/puan) | ✅ Kapandı |
| KAPI 4 (bildirim + guardrail) | ⚠️ Kod tamam; cihaz push elle test bekliyor |
| KAPI 5 (paywall + analitik) | ⚠️ SDK + IAP sandbox E2E bekliyor |
| KAPI 6 (store canlı) | ⏸ Yapı hazır; yayınlama bekliyor |
