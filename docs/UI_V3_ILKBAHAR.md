# UI v3 — "İLKBAHAR" (Cursor ekran turu planı)

> Kaynak: 28 Temmuz yatırımcı toplantısı — "Arayüz pastel, uygulama bana
> ilkbaharı hissettirmeli, sonbaharı değil. Her bölüm daha profesyonel."
> Adım 0 (palet iskeleti) 2026-07-29'da koda entegre edildi (Claude Cowork).
> Bu doküman Cursor'ın UI şeridi için tek referanstır; FAZ 8 görev sırasını
> BOZMAZ — 8.4 ile paralel şerit olarak yürür (önce 8.1/8.2!).

## Tasarım felsefesi (her karar buna hesap verir)

Niyetsen "365 günlük dönüşüm" satıyor. Sonbahar paleti (kuru kil, soluk bej)
"bitiş" hissi veriyordu; İlkbahar = **büyüme, filiz, sabah ışığı**. Ama canlılık
≠ neon oyuncak: hedef "profesyonel enerji" — Headspace'in sıcaklığı +
Duolingo'nun canlılığından bir tık olgunu.

Üç duygu kelimesi: **taze, güvenli, ödüllendirici.** Bir ekran bu üçünden
birini vermiyorsa dokunma.

## Adım 0 — TAMAMLANDI (token değişimi, tüm app otomatik yenilendi)

`mobile/src/constants/theme.ts` yeni değerler (anahtar adları değişmedi):

| Token | Eski (sonbahar) | Yeni (ilkbahar) | Niyet |
|---|---|---|---|
| background L | #F1E7D9 bej | **#F6F7EE** güneşli krem | kahve tonu gitti, yeşil alt ton |
| backgroundElement L | #FBF6EF | **#FEFEF8** | kartlar zeminden net ayrışır |
| text L | #2C241C kahve | **#1F2A1E** koyu yaprak | kontrast ↑ ("pastel" şikâyetinin ilacı) |
| tint | #6E7856 kuru zeytin | **#35814A** genç yaprak | ana kimlik: büyüme |
| accentWarm | #B4623C kiremit | **#E06842** çiçek mercanı | enerji/ödül vurgusu |
| backgroundSelected | bej | **#DCEEDD** yeşil yıkama | seçim = canlanma |
| Gölgeler | kahve #9A4E2E | yaprak #2F6632 / mercan | ışık ilkbahar güneşi |
| Dark tema | kahve gece | **orman gecesi** #131A12 + parlak filiz #7FD08B | |
| Mystic tint | %10 doygunluk ↑ | lavanta canlandı, kimlik korundu | |

Kural değişmedi: **hex hardcode yasak, token kullan.**

## Adım 1 — Hardcode temizliği (yarım gün, İLK UI İŞİ)

Tokenları delen 11 nokta — hepsini `useThemeColor`/token'a çevir:

- `src/app/fal.tsx:254` ActivityIndicator #3B3327 → text token
- `src/app/daily.tsx:368` aynı, `:664` #FBF7EF → backgroundElement
- `src/app/explore.tsx:217` #FCF4EA → onAccent
- `src/components/project-sheets.tsx:615` shadowColor → Shadows token
- `src/components/animated-icon.tsx:115,147,177,236` + `animated-icon.web.tsx:106`
- `src/components/app-tabs.web.tsx:89`

KAPI: `grep -rn "#[0-9A-Fa-f]\{6\}" src/app src/components --include="*.tsx"`
yalnız theme.ts import'u dışında 0 sonuç; iki temada da görsel kontrol.

## Adım 2 — Sohbet ekranı (1 gün; uygulamanın kalbi, demo yüzü)

- Asistan balonu: backgroundElement + SurfaceEdge üst çizgisi + Shadows.subtle;
  kullanıcı balonu: tint dolgu + onAccent metin. Balon girişi: 12px yukarı
  kayma + fade (Motion.base, stagger YOK — sohbet akışkan hissetmeli).
- "Düşünüyor" göstergesi (chain-thinking-indicator): nokta rengi tint'e döner —
  filiz yeşili nabız.
- Hızlı yanıt çipleri: surfaceMuted zemin, basılınca backgroundSelected'a
  yaylanır (scale 0.97, spring).
- Boş sohbet durumu: tek satır davet + 3 örnek çip ("Bu yıl ne değişsin?").
- KAPI: gerçek cihazda sohbet "canlı ama sakin" — animasyon 300ms'i aşmaz.

## Adım 3 — Bugün/Görevler (daily.tsx) (1-1,5 gün; ödül hissinin evi)

- Günün ilerlemesi: ekran üstüne ince **ilerleme halkası veya dolan filiz
  çubuğu** (progressTrack üstüne tint dolgu, Motion.slow ile dolar).
- Görev tamamlama ânı: kart hafif yaylanır + **yaprak konfetisi** (6-8 parçacık,
  tint/accentWarm/success renkleri, 600ms, `isReduceMotionEnabled` true ise
  yalnız renk geçişi). Puan rozeti count-up-text ile sayar (mevcut bileşen).
- Kart hiyerarşisi: sıradaki görev Shadows.hero, kalanlar lifted; tamamlanan
  görev surfaceMuted'a söner (kaybolmaz — gün sonunda "bak neler yaptın").
- Boş gün durumu: "Bugün planında görev yok — bonus ister misin?" + eylem.
- KAPI: tamamlama akışı 10 kez üst üste takılmadan; reduce-motion'da sorunsuz.

## Adım 4 — Plan & Vision Board (1 gün)

- Görsel kartlarda ImageScrim yeni koyu-yaprak tonu; başlık tipografisi
  Fraunces (serif) — vizyon kartları "dergi kapağı" hissi.
- Gün şeridi: bugün tint halkasıyla işaretli; geçmiş günler soluk, gelecek
  günler kilit ikonu YOK (davetkâr, cezalandırıcı değil).
- 8.3 plan düzenleme UI'ı bu dille yapılır (action sheet backgroundElement +
  lifted).
- KAPI: iki farklı planın board'ları arasında geçişte kimlik tutarlı.

## Adım 5 — Rank/Puan (rank.tsx) (yarım gün)

- Kategori rozetleri categoryBadge yeni yeşiliyle; rank ilerlemesi halka
  grafiği (tint), seviye atlama ânında Shadows.clay (mercan) parlaması.
- Zincir: alev yerine **filiz metaforu** değerlendir (gün sayısı büyüdükçe
  yaprak sayısı artar) — İlkbahar diliyle bire bir. Basit SVG/emoji kademesi
  yeter: 🌱→🌿→🌳 (3/7/30 gün).

## Adım 6 — Profil (settings.tsx) (8.4 ile BİRLEŞİK)

FAZ8_LANSMAN 8.4 maddesi geçerli; bu palette uygulanır. Avatar halkası tint,
burç sembolü textSecondary, cinsiyet seçici chip'leri backgroundSelected.

## Adım 7 — Mistik ekranlar (yarım gün)

- MysticColors canlandırılmış lavanta ile zaten yenilendi; kartlarda
  SurfaceEdge + lifted uygula, tarot animasyonuna dokunma (çalışıyor).
- Mistik ↔ ana tema geçişinde zemin rengi crossfade (Motion.base).

## Mikro-etkileşim sözlüğü (tüm ekranlarda ortak dil)

- Basılabilir her şey: pressed'de scale 0.97 spring + opacity 0.9.
- Liste girişleri: Motion.stagger (60ms) ile alttan 8px fade — YALNIZ ilk
  render'da, her scroll'da değil.
- Başarı = yeşil + yukarı hareket; kayıp = mercan değil KIRMIZI DEĞİL,
  textSecondary + sarsılmaz ton (utandırma yasağı görselde de geçerli).
- Skeleton: surfaceMuted üstünde parıltı (shimmer), spinner yalnız kısa işler.

## Değişmezler

- Token anahtarları ve bileşen API'ları değişmez; Easing yalnız reanimated'dan.
- Metin kontrastı: gövde ≥ 4.5:1, büyük başlık ≥ 3:1 (iki temada da).
- iPhone SE + büyük Android; her adım = 1 commit (`faz8-ui: ...`); her adımda
  `npx tsc --noEmit` 0 hata + gerçek cihaz.
- Sıra: Adım 1 → 2 → 3 → 4 → 5 → 6 → 7. Adım atlama yok; her adımın KAPI'sı var.
