# FAZ 5 — Aktif Plan (tek açık görünüm)

> FAZ 0–4 kapandı. Bu dosya Cursor sağ panel / plan için **yalnızca aktif faz**.
> Tam arşiv: `NIYETSEN_MASTER_PLAN.md` §3.

## ⏸ DURAKLATILDI — Mağaza hesapları bekleniyor

**Devam anahtarı:** `CANLI YA DEVAM APP`  
Bu ifadeyi yazdığında: bu sohbetten itibaren yapılan tüm değişikliklerle birlikte Apple ($99) + Google ($25) kayıt ve KAPI 5 sandbox IAP'ten devam ederiz.

**Şu an:** Para gelene kadar **Expo Go + lokal ağ** ile geliştirme, QC, UX/UI, mockup.

### Lokal Expo Go checklist
1. Backend: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
2. `mobile/.env` → `EXPO_PUBLIC_API_URL=http://<Mac LAN IP>:8000` (fiziksel cihaz)
3. `npx expo start -c` (env değişince cache temizle)
4. Supabase auth ile giriş (JWT zorunlu)

## KAPI 5 kapanış kriteri (hesap açılınca)

Sandbox satın alma → webhook/sync → `active` → kilitler açılır → Geri Yükle → iptal testi.

## Kod durumu (hazır)

- [x] Backend: trial, paywall kilidi, webhook, `/me/subscription/sync`
- [x] Mobil: paywall, RevenueCat SDK, polling, PostHog event'leri
- [x] Railway: `REVENUECAT_WEBHOOK_SECRET` + `REVENUECAT_ENTITLEMENT_ID` + `REVENUECAT_API_KEY`
- [x] Backend RC secret API key (lokal)
- [ ] Apple Developer ($99) + Google Play ($25)
- [ ] iOS + Android public RC key'leri (mağaza hesabı sonrası)
- [ ] Mağaza IAP ürünleri + sandbox E2E

## CANLI YA DEVAM APP — o zaman yapılacaklar

Detay: `docs/KAPI5_REVENUECAT_SETUP.md`

1. Apple + Google developer kayıt
2. App Store Connect P8 + Play subscription ürünleri
3. RevenueCat iOS/Android app tamamla → `appl_` / `goog_` key
4. `python -m scripts.setup_kapi5_secrets`
5. EAS preview build → sandbox satın alma testi

## Push bekleyen

- Mobile repo: 2 commit (`288e7ba`, `f78d471`) origin'de değil
