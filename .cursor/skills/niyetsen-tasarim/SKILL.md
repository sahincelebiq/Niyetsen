---
name: niyetsen-tasarim
description: Niyetsen mobil uygulamasının tasarım sistemi ve UI/UX kalite kontrolü. Niyetsen'de HERHANGİ bir ekran, bileşen, stil, tipografi, renk, animasyon, paywall/premium kapısı veya "arayüz hantal/büyük/karışık" şikâyeti üzerinde çalışırken bu skill'i kullan. Yeni ekran tasarlarken, mevcut ekranı elden geçirirken, premium içerik kapısı eklerken veya tasarım incelemesi yaparken de geçerli.
---

# Niyetsen Tasarım Sistemi (v3.1 — İlkbahar + Minimal)

Niyetsen'in görsel dili iki karardan doğar: **İlkbahar** (yatırımcı geri
bildirimi: "sonbahar değil ilkbahar hissettirmeli") ve **Minimal** (Şahin:
"çok hantal, çok kalın, çok büyük"). Bu skill her UI işinde bu iki kararı
korur. Tek gerçek kaynak her zaman koddur: `mobile/src/constants/theme.ts`
ve `mobile/src/components/themed-text.tsx` — buradaki değerlerle çelişirsen
kod kazanır.

## 1. Tipografi — KİLİTLİ minimal ölçek

| ThemedText type | Boyut | Kullanım |
|---|---|---|
| `title` | 32 / 38 (Fraunces) | Hero anları — ekran başına EN FAZLA 1 |
| `screenTitle` | 22 / 28 (Fraunces) | Ekran başlığı |
| `subtitle` | 18 / 24 (Fraunces Medium) | Kart/bölüm başlığı |
| `default` | 16 / 25 (Manrope Medium) | Gövde |
| `small` / `smallBold` | 14 / 21 | İkincil bilgi, rozet, buton |

Neden kilitli: eski ölçek (44/30/28) uygulamayı web sitesi gibi gösteriyordu.
Vurgu gerekiyorsa **puntoyla değil boşluk ve renkle** ver: başlığı büyütme,
üstüne Spacing.four koy veya tint rengi kullan. Yeni fontSize değeri yazmak
yerine önce bu tabloya uydur; tablo yetmiyorsa Şahin'e sor.

## 2. Renk — İlkbahar token'ları

Hex hardcode YASAK; her renk `theme.ts` token'ı: `tint` #35814A genç yaprak
(birincil), `accentWarm` #E06842 çiçek mercanı (ödül/enerji), zemin güneşli
krem, koyu tema "orman gecesi". Fal/mistik ekranlar `MysticColors` kullanır.
Metin kontrastı: gövde ≥ 4.5:1, büyük başlık ≥ 3:1 — iki temada da test et.
Fiziksel sahne yoksa tema token'ı dışına çıkma.

## 3. "KAPI İÇERİDE" premium deseni (Şahin kuralı, 2026-08-05)

Ücretli bölümler (rapor, İdol detayı, premium haklar) ücretsiz kullanıcıya
**GÖRÜNÜR ve GİRİLEBİLİR** — kullanıcı asla ekrandan dışarı atılmaz.

- ❌ `useRequirePremium` ile `router.replace('/paywall')` — kullanıcı ne
  kaçırdığını hiç göremez, dönüşüm düşer.
- ✅ `usePremiumAccess` ile ekran açılır; içerik yerine **kilitli önizleme
  kartı** gösterilir: değer vaadi 1-2 cümle + "PRO ile aç" CTA (44pt,
  `tint` dolgu) + `router.push('/paywall')`. Örnek uygulama: `rapor.tsx`.
- Fal (tarot/kahve/el): ekran **açık kalır** (kapı içeride). Ücretsiz ömür
  boyu 1 kahve + 1 tarot + 1 el + sınırlı mistik sohbet; hak bitince kilit
  önizleme + "PRO ile aç". Burç sınırsız. Fal modülüne `replace('/paywall')
  ekleme — geçmişte "mistik çalışmıyor" hatası yarattı.
- Felsefe Yolları: liste + detay ücretsiz incelenir; "bu yolla başla" PRO.
- Rapor: 7 günlük özet ücretsiz; 30 günlük hikâye PRO (panel açık kalır).
- Zincir yoldaşı: yalnız Filiz ücretsiz; diğer avatarlar görünür, seçim PRO.
- Sunucu her zaman son sözü söyler (402); istemci kapısı yalnız UX içindir.

## 4. Hareket ve etkileşim

- `Easing`/`Animated` YALNIZ `react-native-reanimated`'dan (react-native'ten
  import = worklet crash; eslint kuralı var, kaldırma).
- Süreler `Motion` token'ından (fast 180 / base 260 / slow 420 / stagger 60);
  tavan ~300ms — uygulama "canlı ama sakin".
- Her animasyonda `AccessibilityInfo.isReduceMotionEnabled` saygısı.
- Basılabilir her şey: pressed'de scale 0.97 + opacity; dokunma hedefi ≥ 44pt.
- Durum üçlüsü zorunlu: yükleniyor (skeleton/spinner) + boş durum (tek cümle
  + eylem) + hata (error-banner + tekrar dene).

## 5. Ton (görsel dil dahil)

Kayıp hissi + kimlik ✅ ("23 günlük zincirin seni bekliyor"), utandırma ❌.
Raporda/kutlamada yalnız kazanımlar; ceza görselleştirilmez. Kullanıcı metni
her zaman Türkçe; "task/pending" gibi İngilizce sızıntı yasak.

## 6. Ekran QA kontrol listesi (her UI değişikliğinden önce çalıştır)

1. Tipografi tabloya uyuyor mu? Ekranda 1'den fazla `title` var mı?
2. Hex hardcode var mı? (`grep -n "#[0-9A-Fa-f]\{6\}" <dosya>`)
3. İki temada (açık/koyu) kontrast ve taşma kontrolü — iPhone SE genişliği
   (375pt) referans.
4. Premium içerik varsa: kapı İÇERİDE mi? Kullanıcı dışarı atılıyor mu?
5. Yükleniyor/boş/hata durumları tasarlandı mı?
6. `npx tsc --noEmit` 0 hata; animasyon varsa reduce-motion denendi mi?
7. Dokunma hedefleri ≥ 44pt; accessibilityLabel/Role atandı mı?

## Dosya haritası

- Token'lar: `mobile/src/constants/theme.ts` (Colors, MysticColors, Spacing,
  Radii, Shadows, Motion, SurfaceEdge, ImageScrim)
- Tipografi: `mobile/src/components/themed-text.tsx`
- Kapı-içeride örneği: `mobile/src/app/rapor.tsx`; serbest fal örneği:
  `mobile/src/app/mystic.tsx`
- Ekran turu planı: `docs/UI_V3_ILKBAHAR.md`; burç: `constants/zodiac.ts`
