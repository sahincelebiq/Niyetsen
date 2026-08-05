---
name: niyetsen-play-store-listing
description: Niyetsen Google Play store listing assets — screenshots, feature graphic, promo video, copy. Use when filling Play Console Mağaza girişi / store listing, uploading phone screenshots, feature graphic 1024x500, or YouTube preview video.
---

# Niyetsen Play Store Listing (vitrin)

## Status reality check

- **Dahili test yayınlandı** ≠ herkese açık mağaza. App appears for testers on the internal testing link only.
- Public listing needs: store listing assets complete + Data safety + content rating + production/closed track when ready.
- Package: `com.niyetsenai`. Do not change. Updates = new AAB with higher `versionCode`.

## Asset source of truth

| Asset | Path / rule |
|-------|-------------|
| Phone screenshots (Play) | `store-listing/phone/play_1080x1920/01_*.png` … `07_*.png` — upload **01→07 order** |
| iOS (later) | `store-listing/phone/ios_1290x2796/` |
| Regen screenshots | `cd store-listing && python3 generate_screenshots.py` |
| Index / narrative | `store-listing/INDEX.md` |
| App icon | `mobile/assets/images/icon.png` (Play: 512×512 PNG) |
| Feature graphic | `store-listing/feature/feature_1024x500.png` (required for listing) |
| Promo video | YouTube **public or unlisted** URL only — no raw MP4 upload |

Fal/mystic: **secondary** in store copy; no scare claims; entertainment disclaimer if mentioned.

## Play Console path (Turkish UI)

`Kullanıcı sayısını artırın` → `Play Store'daki varlığı` → `Mağaza girişleri` → `Varsayılan mağaza girişi`

### Step 1 — Varlıklar (this page)

1. Scroll past “Yaygın metin öğeleri”.
2. **Uygulama adı** (≤30): `Niyetsen — Yaşam Asistanı` (or shorter `Niyetsen`).
3. **Kısa açıklama** (≤80): `Niyetini sohbetle plana çevir. Fotoğrafla kanıtla. Zincirini koru.`
4. **Uzun açıklama**: chat → visual daily plan → photo proof → streak/points. Honest tone, no shaming. Fal optional/entertainment.
5. **Grafik varlıklar**
   - Uygulama simgesi: 512×512
   - Özellik grafiği: **1024×500** (`store-listing/feature/feature_1024x500.png`)
   - Telefon ekran görüntüleri: `play_1080x1920` 01→07 (min 2, max 8)
   - Tablet: optional for now
6. **Tanıtım videosu** (optional but recommended): paste YouTube URL only.
7. `Taslak olarak kaydet` or `İleri` → Yorum → gönder.

### Step 2 — Video (İKİ YOL; 2026-08-05'te güncellendi)

**Yol A — hazır MP4 (Claude Cowork üretti, anında yayınlanabilir):**
`store-listing/video/niyetsen_promo_1920x1080.mp4` (~18 sn, 7 vitrin karesi +
başlık/CTA kartları, marka fontları). Yeniden üret:
`cd store-listing && python3 generate_promo_video.py` (ffmpeg gerekir).
Müzik yok — YouTube Studio'da telifsiz sakin akustik (90-100 BPM) ekle.
YouTube'a **liste dışı (unlisted)** yükle → linki Play "Tanıtım videosu"na yapıştır.

**Yol B — gerçek ekran kaydı (v2, daha güçlü; hazır olunca A'yı değiştir):**
1. Cihazda 15–30 sn kaydet, sıra: sohbet → plan oluşur → Bugün → kanıt onayı →
   zincir (mistik İLK KAREDE OLMAZ — Apple 4.3 / konumlama).
2. 1080×1920 dikey veya 16:9; başka marka filigranı yok.
3. YouTube (unlisted) → link → Play alanı. MP4 asla ekran görüntüsü yuvasına yüklenmez.

### Varlık üretim mimarisi (değiştirme, kullan)

- Tipografi: **Fraunces 600** başlık + **Manrope 500/800** gövde — TTF'ler
  `mobile/node_modules/@expo-google-fonts/...` yolundan okunur (macOS + CI uyumlu).
  Arial'a dönme; scriptler fallback'i kendisi halleder.
- Feature graphic v2 (2026-08-05): krem okunurluk paneli + koyu yaprak metin +
  Sohbet→Plan→Kanıt→Zincir çipleri. Açık zemine beyaz yazı YASAK (v1 hatası).
- Play icon: `store-listing/icon/icon_512x512.png` (1024 kaynaktan üretilmiş,
  164 KB ✓). Kaynak: `mobile/assets/images/icon.png`.
- iOS seti (`phone/ios_1290x2796/`) App Store turundan önce yeniden üretilmeli
  (eski fontla kalmış olabilir): `python3 generate_screenshots.py` tam koşu.

### Step 3 — After listing draft

Still needed for broader release (not blocking internal test install):

- [ ] Data safety form
- [ ] Content rating questionnaire
- [ ] Target audience / news apps declarations if asked
- [ ] Internal testers list + opt-in link share
- [ ] Production track only when listing + policies green

## Commands

```bash
# Regenerate marketing screenshots
cd store-listing && python3 generate_screenshots.py

# Feature graphic (if script exists)
cd store-listing && python3 generate_feature_graphic.py
```

## Copy locked snippets (TR)

**Title ≤30:** `Niyetsen — Yaşam Asistanı`  
**Short ≤80:** `Niyetini sohbetle plana çevir. Fotoğrafla kanıtla. Zincirini koru.`

## Do not

- Upload `store-listing` folder as AAB
- Use iOS 1290×2796 set as Play phone shots (use `play_1080x1920`)
- Lead store creatives with fal/tarot
- Change `android.package` / upload keystore casually
