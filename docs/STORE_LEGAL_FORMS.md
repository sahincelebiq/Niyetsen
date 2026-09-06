# Mağaza yasal formları — Play Data Safety + App Store Privacy

Şahin’in Play Console ve App Store Connect’te **dürüst** dolduracağı cevaplar.
Kaynak: gerçek ürün (Gemini, Supabase, IAP, in-app kamera, konum yok).
Bu dosya avukat onayı değildir; yayın öncesi hukukçu bakışı önerilir.

**Kanonik URL’ler (mağazaya yapıştır):**

| Alan | URL |
|------|-----|
| Privacy policy | https://niyetsen.com/privacy.html |
| Terms of use | https://niyetsen.com/terms.html |
| Account deletion (Play zorunlu) | https://niyetsen.com/account-deletion.html |
| TR yedek | https://niyetsen.com/gizlilik.html · https://niyetsen.com/hesap-silme.html |

Paket: `com.niyetsenai` (Play skill). iOS bundle `com.niyetsen.app` olabilir — ikisi de metinde geçer.

Yaş: **18+**. Families / Designed for Children: **Hayır**.

---

## Google Play — Veri güvenliği (Data safety)

**Veri toplanıyor mu?** Evet.

**Veri satılıyor mu?** Hayır.

**Kullanıcı silme talep edebilir mi?** Evet (Profil → Hesabımı Sil + URL).

**Aktarımda şifreleme?** Evet (HTTPS / JWT).

### Toplanan türler (işaretle)

| Tür | Toplanır | Amaç | Paylaşılır | Not |
|-----|----------|------|------------|-----|
| Ad | Evet | Uygulama işlevi, hesap | Hayır (üçüncü taraf reklam yok) | Profil |
| E-posta | Evet | Hesap | Hayır | Auth |
| Kullanıcı kimlikleri | Evet | Hesap | RevenueCat / mağaza (abonelik) | Supabase + Apple/Google id |
| Fotoğraflar | Evet | Uygulama işlevi | **Google Gemini** (kanıt/fal değerlendirme) | Yalnız in-app kamera; galeri yok; biyometri yok |
| Kişisel mesajlar / kullanıcı içeriği | Evet | Uygulama işlevi | **Google Gemini** (sohbet, plan, fal) | |
| Satın alma geçmişi | Evet (durum) | Uygulama işlevi | RevenueCat, Apple/Google | Kart numarası Niyetsen’de yok |
| Uygulama etkileşimi | Yalnız PostHog anahtarı varsa | Analitik | PostHog | Anahtar yoksa işaretleme |
| Kilitlenme günlükleri | Yalnız Sentry DSN varsa | Hata | Sentry | Yoksa işaretleme |
| Cihaz veya diğer kimlikler | Oturum / teknik | Güvenlik, işlev | Hayır (reklam kimliği yok) | |

**İşaretleme:** Konum (hassas/yaklaşık) **Hayır**. Rehber **Hayır**. Takvim **toplanmaz** (kullanıcı kendi takvimine eklerse cihaz tarafı). Sağlık **Hayır** (kullanıcı sohbette yazarsa içerik olarak gider — istenmez). Finansal kart **Hayır**.

**Zorunlu mu?** Hesap için ad/e-posta evet. AI sohbet ve fotoğraf **rıza ile**; rıza yoksa hesap kalır.

**Çocuklara yönelik mi?** Hayır.

**Reklam / ATT takip?** Hayır.

---

## App Store Connect — App Privacy (nutrition labels)

**Tracking (ATT)?** Hayır — `NSUserTrackingUsageDescription` yok; reklam kimliği yok.

Bağlı veri (Linked to User), amaç **App Functionality** (ve varsa Analytics / Crash Data):

| Privacy type | Collected | Linked | Tracking | Used for |
|--------------|-----------|--------|----------|----------|
| Contact Info — Name | Yes | Yes | No | App Functionality |
| Contact Info — Email | Yes | Yes | No | App Functionality |
| Identifiers — User ID | Yes | Yes | No | App Functionality |
| User Content — Photos or Videos | Yes | Yes | No | App Functionality (Gemini) |
| User Content — Other User Content | Yes | Yes | No | App Functionality (chat/plan) |
| Purchases — Purchase History | Yes | Yes | No | App Functionality |
| Sensitive Info | No (not requested) | — | — | — |
| Location | No | — | — | — |
| Usage Data — Product Interaction | Only if PostHog live | Yes | No | Analytics |
| Diagnostics — Crash Data | Only if Sentry live | Yes | No | App Functionality / Analytics |
| Other Data — Other | Birth date, optional gender, timezone, language, scores | Yes | No | App Functionality |

**Third-party sharing:** Google (Gemini inference). Declare as used by a third party for the app’s functionality, not advertising.

---

## Apple 3.1.2 paywall kontrolü

Uygulamada olmalı (kodda var):

- [x] Mağazadan gelen gerçek fiyat (uydurma yok)
- [x] Satın alımları geri yükle
- [x] Koşullar + Gizlilik linki
- [x] Otomatik yenileme / 24 saat / iptal yolu metni (`paywall.renewalNote`, her dil)

App Store Connect abonelik grubu: süre + fiyat + gizlilik URL.

---

## Play / Apple diğer beyanlar

- **Fal / mistik:** store metninde ikincil; “eğlence, tıbbi/hukuki/finansal tavsiye değil”.
- **Sağlık uygulaması değil.**
- **UGC:** sohbet kullanıcı içeriği; kabul edilebilir kullanım koşullarda.
- **Hesap silme:** in-app + URL (Play 2023+ kuralı).
- **Sign in with Apple:** Google girişi varsa iOS’ta Apple girişi zorunlu (ürün kuralı; bu sprintte form değil).
- **Content rating:** 18+ / yetişkin; şiddet yok; kullanıcı metni olabilir.

Site canlı değilse mağaza URL’si 404 verir — `website/` Hostinger’a deploy edilmeden form gönderilmesin.
