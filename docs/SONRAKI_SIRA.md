# Sonraki sıra (kilit, 2026-08-16 — Şahin)

> Şahin 16 Ağu 16:36: RC kimlik arkada beklesin, sıradan ilerle, paywall UI,
> rapor için **önce soru**. Model / mistik ajan / CNN katmanı hâlâ “devam et”.

Play Console **Kapalı test — Alpha `10 (1.0.1)`** inceleme/yayın.
RevenueCat JSON yüklü; **Credentials need attention** Google gecikmesi
(dakika–24 saat). Play daveti Active.

## Sıra

0. Alpha yayınla + (isteğe) aynı AAB dahili teste — **sen**
1. RC Valid + ürün `niyetsen_monthly:monthly` / `niyetsen_yearly:yearly` bağla — **sen + ben**
2. **Ödeme UI** — kodda İlkbahar paywall (150 / 1.200 fallback) **bu oturumda yapıldı**. Mağaza fiyatı RC yeşillenince gelir.
3. **Raporlar** — sonsuz spinner kapatıldı. Şahin kilit (16 Ağu):
   açılış = **Panel**; üstte **1 cümle ayna** (6 yön + erteleme örüntüsü,
   kaçırılan listesi/ceza yok) + altında kazanım KPI. Hikâye isteyene.
   `mirror_line` backend’de kural bazlı (Gemini yok).
4. Mistik akışlar
5. Ana sohbet ajanı
6. Örüntüleme (ConvNet yok)
7. MiniMax-M3 yalnız aday

## UI planı (İlkbahar, Fraunces/Manrope, Reanimated)

| Ekran | Ne |
|---|---|
| Paywall | 1 title, 3 vaat (plan/kanıt/rapor; fal ücretsiz), yıllık önerilen `tint` CTA, aylık sakin, geri yükle + yasal |
| Rapor | Önce açılır panel; sonra “neden / nasıl” — utandırma yok, yalnız kazanım + dürüst yüzleşme |
| Mistik | Hub sohbet; tarot/kahve/el/astro kısayol; `MysticColors`; ComingSoon canlı rotada yok |
| Ajan | `core/tools.py` dışı araç yok; bellek + niyet |

Fiyat kilit: aylık **150 TL**. Yıllık fallback **1.200 TL** (150×8) ta ki Play’deki yıllık netleşene.

Play Console şu an **Kapalı test — Alpha `10 (1.0.1)`** inceliyor.
Yönetilen yayınlama açık → inceleme bitince otomatik yayılmaz; **Yayın özeti**
üzerinden sen yayınlarsın.

## Sıra (tek tek, “devam et” ile)

0. **Şimdi (sen + Play):** Alpha incelemesi + gerekirse aynı AAB’yi **Dahili test**e de yükle. Aşağıdaki “Dahili test” bölümü.
1. **RevenueCat + Play IAP** — sen dashboard; ben ürün ID’lerini bağlarım. Paywall UI sonra.
2. **Ödeme ekranı UI** — mevcut `paywall.tsx` üzerine Figma → kod (İlkbahar, Fraunces/Manrope, Reanimated only).
3. **Raporlar** — tıklayınca açılmıyor; önce açılır yap, sonra örüntü katmanı.
4. **Mistik** — sohbet / tarot / fal / el / astroloji / fal geçmişi çalışır + tasarım.
5. **Ana sohbet ajanı** — mevcut `core/tools.py` dışına araç eklenmez; bellek + niyet + dürüst yüzleşme güçlenir.
6. **Örüntüleme (CNN metaforu, ConvNet eğitimi YOK)** — 6 kategori + erteleme/mazeret/zincirden “neden erteliyor / neden özgüvensiz / nasıl irade” katmanı. v1 fine-tuning YASAK.
7. **Model istişaresi (şimdi karar yok)** — Gemini 3.1 Pro durur; MiniMax-M3 aday, A/B sonra. Kanıt Vision Gemini’de kalır ta ki MiniMax görsel kanıt KAPI’sı geçene kadar.

## Dahili test ≠ Kapalı test (Alpha)

Play’de bunlar **ayrı ray**. Biri dolunca diğeri güncellenmez.

| Ray | Menü | Kim görür | 1.0.1 (v10) |
|-----|------|-----------|-------------|
| **Dahili test** | Test edin ve yayınlayın → Test → **Dahili test** | Yalnız dahili liste + o rayın opt-in linki | Hâlâ **5 Ağustos** yazıyorsa bu raya v10 **yüklenmemiş** demektir. Normal. |
| **Kapalı test (Alpha)** | Test edin ve yayınlayın → Test → **Kapalı test** | Kapalı test e-posta listesi + Alpha opt-in | Ekrandaki inceleme **burası**. Busra buradaysa burayı bekler. |

Aynı AAB iki raya da yüklenebilir; versionCode 10 her ikisinde de geçerli.
Dahili testteki tester kapalı testi görmez (ve tersi), opt-in linki farklıdır.

**Yönetilen yayınlama:** “hızlı kontrol 7 dk” ≠ kullanıcıda güncelleme.
Kontrol bitince Yayın özeti → değişiklikleri **yayınla**. Sonra tester
Play Store’da uygulamayı açıp güncellemeyi çeker (bazen 1–2 saat).

## RevenueCat — senin tıklama yolu (ürünler henüz boş)

Kod + RC iskelet hazır: Play app `com.niyetsenai`, entitlement `premium`,
offering `default` (paketsiz). **Products listesi boş** — satın alma
“paket bulunamadı” der ta ki sen Play aboneliğini açıp bağlayana kadar.

### A. Play Console (önce burası)

1. Sol menü **Google Play ile para kazanın** → **Ürünler** → **Abonelikler**.
2. Abonelik oluştur:
   - Ürün kimliği: `niyetsen_monthly` (sonra değişmez)
   - Temel plan kimliği: `monthly`
   - Fiyat: **150 TL / ay**, Türkiye (2026-08-16 Şahin; eski 450 kiliti kalktı)
3. İkinci abonelik:
   - Ürün: `niyetsen_yearly`
   - Temel plan: `yearly`
   - Yıllık fiyat: Şahin sonra (eski 3.600 kiliti durur; aylık 150’ye göre yeniden seçilecek)
4. **Ayarlar → Lisans testi** — sen + Busra + kapalı test e-postaları.
5. Abonelikler **aktif** olmalı (taslak yetmez). Kapalı/dahili AAB yüklü
   uygulamada test satın alma lisans testi ile ücretsiz geçer.

### B. RevenueCat (Play ID’leri birebir)

1. [app.revenuecat.com](https://app.revenuecat.com) → proje **Niyetsen**
2. **Apps** → **Niyetsen Play** (`com.niyetsenai`) — yeni app açma
3. Play service account JSON’u Apps → Play Store credentials’a yükle
   (yoksa ürünler “unattached” kalır)
4. **Products** — store identifier formatı zorunlu:
   - `niyetsen_monthly:monthly`
   - `niyetsen_yearly:yearly`
5. **Entitlements → premium** → bu iki ürünü bağla
6. **Offerings → default** (current) → paketler:
   - Monthly → `$rc_monthly`
   - Annual → `$rc_annual`
7. **Integrations → Webhooks** (yoksa):
   - URL: `https://api-production-86f1.up.railway.app/webhooks/revenuecat`
   - Authorization: `Bearer <Railway REVENUECAT_WEBHOOK_SECRET>`

Android public key EAS `play-internal` / `production` içinde.
Yeni AAB gerekmez; ürün bağlanınca mevcut 1.0.1 mağaza fiyatını çeker.

Bittiğinde sohbette ürün ID’lerini yaz — ben RC tarafını bağlarım / doğrularım.

## Model notu (karar kilitlenmedi)

| | Gemini 3.1 Pro (şimdi) | MiniMax-M3 (aday) |
|--|------------------------|-------------------|
| Resmi ad | `gemini-3.1-pro-preview` | `MiniMax-M3` (docs, 2026-06) |
| Metin fiyat (1M token) | ~$2 in / $12 out (≤200k) | ~$0.30 in / $1.20 out (≤512k, kampanya) |
| Kanıt foto | Vision hazır, canlı | Multimodal iddia var; **su≠meyve KAPI’sız geçiş YOK** |
| Araçlar | `core/tools.py` + thinking_level çözüldü | Function calling A/B şart |
| Risk | Kota / maliyet | TR ton, JWT/prompt enjeksiyon, yeni client |

**Şimdi:** Gemini durur. Key alma serbest; koda bağlama “devam et” + A/B sonra.

## Örüntüleme (CNN) — ne evet / ne hayır

- Evet: mevcut 6 kategori + erteleme / mazeret / sessiz kaçırma / zincir
  katmanlarından “neden / nasıl” örüntüsü. Rapor + sohbet bellek.
- Hayır: ConvNet eğitmek, fine-tuning, yeni puan formülü uydurmak,
  utandırma tonu, public leaderboard.
