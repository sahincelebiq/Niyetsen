# Niyetsen — Mağaza önizleme görselleri (Play + App Store)

**Üretim:** 2026-08-02 · `python3 store-listing/generate_screenshots.py`  
**Kural:** Türkçe yazı AI’da değil; Pillow + marka arka plan. Fal **ikincil** — set’te yok (Apple 4.3).

---

## Anlatı sırası (yükleme sırası = bu sıra)

| # | Dosya | Başlık | Ne anlatır | Neden bu sırada |
|---|--------|--------|------------|-----------------|
| 1 | `01_niyet` | Niyetin konuşulur. Planın yaşanır. | Hook + marka | Arama kartında ilk 1–2 kare kritik |
| 2 | `02_sohbet` | Sohbetle niyetini netleştir | AI rehber sohbet | Ürünün girişi |
| 3 | `03_plan` | Her gün görselli bir plan | Günlük görev kartları | Dönüşüm vaadi |
| 4 | `04_kanit` | Fotoğrafla kanıtla | Kanıt / adil oyun | Farklılaştırıcı mekanik |
| 5 | `05_zincir` | Zincirini koru | Streak + kategoriler | Oyunlaştırma |
| 6 | `06_rapor` | Yolculuğunu gör | Wrapped / rapor | Duygusal kapanış |
| 7 | `07_basla` | Bugün ilk adımını at | CTA | Son kare = hareket |

---

## Klasörler (hazır PNG)

| Klasör | Boyut | Mağaza |
|--------|-------|--------|
| [`phone/play_1080x1920/`](phone/play_1080x1920/) | **1080 × 1920** (9:16) | **Google Play** telefon (önerilen) |
| [`phone/ios_1290x2796/`](phone/ios_1290x2796/) | **1290 × 2796** | **App Store** iPhone 6.7" |

Kaynak arka planlar: [`sources/`](sources/) · Logo: `sources/logo.png`  
Yeniden üret: `cd store-listing && python3 generate_screenshots.py`

---

## Google Play Console’a yükleme

1. Play Console → Uygulama → **Grow → Store presence → Main store listing**
2. **Phone screenshots** → `phone/play_1080x1920/*.png` (01→07 sırayla)
3. Format: PNG, alpha yok, her biri &lt; 8 MB ✅
4. En az 2, en fazla 8 — biz 7 verdik
5. **Feature graphic v2 hazır:** `feature/feature_1024x500.png` · **Play icon:** `icon/icon_512x512.png` · **Video:** `video/niyetsen_promo_1920x1080.mp4` (YouTube unlisted → link)

**Yapma:** iPhone çerçeveli görseli Play’e “Android UI” diye sunma; bu sette jenerik telefon çerçevesi var (OK).

---

## App Store Connect’e yükleme

1. App Store Connect → uygulaman → iOS App → **App Previews and Screenshots**
2. **iPhone 6.7" Display** → `phone/ios_1290x2796/*.png` (01→07)
3. Apple daha küçük sınıflara ölçekleyebilir; 6.7" öncelikli
4. İleride 6.9" (1320×2868) istersen script’e boyut eklenir

---

## Kısa mağaza metni önerisi (TR)

**Başlık (≤30):** `Niyetsen — Yaşam Asistanı`  
**Kısa (≤80):** `Niyetini sohbetle plana çevir. Fotoğrafla kanıtla. Zincirini koru.`  
**Uzun:** Sohbet → görselli günlük plan → foto kanıt → puan/zincir. Utandırmadan dürüst takip. Fal ikincil eğlence alanı (ayrı metinde nazikçe).

---

## Kalite notu / sonraki cilalar

- Bu set **anlatıcı pazarlama kareleri** (UI stilize mock). Store kuralları “gerçek deneyim” ister — en iyi sonuç: Expo Go’dan gerçek ekran kaydı + bu başlık çerçeveleri.
- Gerçek cihaz screenshot’ların olunca `sources/` altına koyup script’i “gerçek UI göm” moduna genişletebiliriz.
- Feature graphic (Play 1024×500) ve App Preview video ayrı iş.

## Hesap / API

Play hesabın ve API anahtarın gelince: AAB yükleme + listing asset sync ayrı oturumda yapılır. Bu paket **şimdiden** Console’a sürükle-bırak hazır.
