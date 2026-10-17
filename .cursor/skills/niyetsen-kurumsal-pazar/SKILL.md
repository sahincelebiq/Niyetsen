---
name: niyetsen-kurumsal-pazar
description: Niyetsen'in kurumsal (B2B2C) wellbeing / İK analitiği pivotu için pazar araştırması hafızası ve araştırma protokolü. Wellbees, YuLife, Viva Insights, Heltia, Meditopia gibi benzer sistemlerin özellik, gizlilik ve fiyat kalıplarını içerir; REA ile rakip uygulama inceleme sınırlarını tanımlar. Kurumsal panel, İK raporu, organizasyon/takım özelliği, PEPM fiyatlama, çalışan verisi gizliliği veya rakip analizi işlerinde kullan.
---

# Niyetsen Kurumsal Pazar (B2B2C pivot araştırma hafızası)

Son tarama: 2026-10-17. Kaynak linkleri [referanslar.md](referanslar.md) içinde.
Yeni veri eklerken tarih yaz; eski veriyi silme, "eski" bölümüne taşı.

## Pivot tanımı (tek cümle)

Niyetsen bireysel niyet→plan→kanıt→puan döngüsünü korur; üstüne **organizasyon
katmanı** gelir: şirket/İK/yönetici, çalışanların *toplulaştırılmış* niyet ve
sosyal aktivite verisini görür, kurumsal niyet ("bu yıl AI kullanımını %X
artırmak") tanımlar, çalışan bunu kişisel plana bağlar. Birey asla tek tek
izlenmez (aşağıdaki gizlilik tabanı).

## Rakip / analog haritası

| Sistem | Ülke | Ne yapar | Niyetsen'e taşınacak kalıp | Niyetsen farkı |
|---|---|---|---|---|
| **Wellbees** | TR | Kurumsal wellbeing: AI öneri, kulüp/meydan okuma/etkinlik, uzman görüşmesi, puan→WellMarket, İK paneli (60+ hazır rapor, anonim nabız, esenlik puanı, 3 aylık rapor, anket, departman bazlı AI duygu analizi) | İK paneli bölümleri; "şirket esenlik puanı"; departman kırılımı; şirketler arası challenge | Niyetsen görev **kanıtlı**; 365 günlük niyet planı; fal/mistik ayna; AI rehber sohbet ücretsiz |
| **YuLife** | UK | Oyunlaştırılmış wellbeing + sigorta: YuCoin, streak, opt-in liderlik tablosu, 24 saatlik düello, HR Insights (MAU, adım, meditasyon dk, challenge benimseme, ödül kullanımı, demografi) | Opt-in liderlik (zaten var: lig rumuz), düello formatı, "ROI raporu" dili | Puan ceza mekaniği (taban 0), 6 kategori, kanıt |
| **Microsoft Viva Insights** | Global | Yönetici içgörüsü; **min grup 5**, farksal gizlilik, maskeli dağılım, kullanıcı opt-out | **Gizlilik tabanı birebir** (aşağıda) | — |
| **Heltia** | TR | Çalışan destek platformu, uzman eşleştirme, onboarding'de kişiselleştirme soruları, Heltia Insights canlı İK raporu + AI aksiyon önerisi | Kayıt sonrası kısa anket → kişiselleştirme; İK paneline "AI aksiyon önerisi" | Uzman ağı yok (v1'de ekleme) |
| **Meditopia for Work** | TR | 15 dil içerik, challenge/takdir/kulüp, AI asistan SOUL, İK paneli anonim, Slack/Teams/SAP entegrasyonu, web+mobil+saat | Web+mobil eşlik; Slack/Teams entegrasyonu v2 adayı; "takdir" özelliği | — |
| **Evital (Eczacıbaşı)** | TR | Giyilebilir veri (stres/uyku/duygu), İK paneli, erken tükenmişlik riski | Giyilebilir **v3** (kapsam dışı); "erken uyarı" dilini kullanma — sağlık verisi özel nitelikli | — |
| **Lattice / 15Five / Weekdone** | Global | OKR: kaskad hedef, haftalık check-in, 1:1, eNPS; ~$9–11 PEPM | **Kurumsal niyet = kaskad hedef** (şirket → departman → kişi); haftalık check-in = Niyetsen gün kapanışı | Oyunlaştırma + kanıt |
| **Habitica** | Global | RPG oyunlaştırma, parti/lonca, görev kaçırınca hasar | Takım görevi ("parti") mekaniği; lig zaten var | Profesyonel raporlama yok (bizde var) |

## Gizlilik tabanı (KVKK + sektör standardı — KİLİT)

1. **Toplulaştırma eşiği k ≥ 5** (Viva Insights min grup 5; yükseltilebilir).
   5 kişiden az departman/takım için rapor **gösterilmez**.
2. Yönetici **hiçbir zaman** tek kişinin görev/plan/sohbet/fal içeriğini görmez.
   Yalnızca: katılım oranı, kategori dağılımı (6 kategori), zincir ortalaması,
   kurumsal niyete bağlı ilerleme yüzdesi, anket toplamları.
3. **Çalışan opt-in** zorunlu ve geri alınabilir; iş ilişkisinde açık rıza tek
   başına zayıf dayanak (KVKK Kurul 2020/404, 2026/2035). Bu yüzden:
   organizasyona katılım **davet + onay**, katılmayan çalışan hiçbir dezavantaj
   yaşamaz (ürün içinde de: puan/rank etkilenmez).
4. Sağlık / psikolojik veri **özel nitelikli** → kurumsal panelde YOK. Fal,
   mistik sohbet, kriz sinyali, "zayıf yön" anketi **asla** organizasyona akmaz.
5. Anonimleştirme = başka veriyle eşleştirilse bile kişi çıkarılamamalı (KVKK
   rehberi). Küçük grup + kesişen filtre = sızıntı; filtre kombinasyonu da
   k ≥ 5 kontrolünden geçer (sunucu tarafı, SQL view'da değil servis katmanında).
6. Erişim yetki matrisi + erişim logu (`org_audit_log`), rol bazlı: owner /
   hr_admin / manager / member.
7. Utandırma yasağı kurumsal panelde de geçerli: "en az aktif çalışan" listesi
   YOK; yalnız grup trendi + öneri.

## Fiyatlama kıyası (2026)

| Model | Aralık | Not |
|---|---|---|
| Dijital wellbeing platform PEPM | $1–3 temel · $5–7.5 orta · $7.5–12+ kapsamlı | Wellable raporu |
| Wellhub işveren payı | $0.50–3 / $7–10 / $49–52 PEPM | Çalışan kendi yükseltir |
| Headspace for Work (küçük işletme) | $69.99 liste → $45–56 / çalışan / yıl | Yıllık, elle yenileme |
| Calm Business | ~$64 / çalışan / yıl | Üçüncü taraf tahmin |
| Lattice OKR | ~$9–11 PEPM | OKR + performans |
| Wellbees / Heltia / Meditopia | Teklif bazlı | TR pazarı yayınlamıyor |

Niyetsen bireysel kilit: aylık 150 TL (RC `niyetsen_monthly:monthly`). Kurumsal
taslak önerisi (karar Şahin): **koltuk başı aylık**, 3 kademe (Takım ≤25 /
Şirket / Kurumsal-teklif); çalışan bireysel PRO'ya **koltukla** ulaşır
(RevenueCat entitlement `premium` kurum tarafından grant edilir — `grant-customer-entitlement`).

## Kullanıcı anketi kalıbı (kayıt sonrası 3 soru — sıra kilit)

1. **Ne amaçla kullanacaksın?** (çoktan seçmeli, çoklu): kişisel gelişim ·
   iş/kariyer hedefi · sağlık/alışkanlık · sosyal hayat · şirketim davet etti ·
   ekibimi yönetmek
2. **Kendinde eksik gördüğün yön?** 6 kategoriden seç (İrade, İstikrar,
   Disiplin, Özgüven, Sosyallik, Özsaygı) + serbest metin (opsiyonel). **Yalnız
   kişiye özel**, organizasyona akmaz.
3. **Bizi nereden duydun?** (en son): arkadaş · şirketim · sosyal medya ·
   mağaza araması · blog/web · diğer.

Heltia ve Wellbees de kayıt sonrası kişiselleştirme sorusu soruyor; sektör
normu 3–5 soru, atlanabilir.

## REA ile rakip inceleme protokolü (yasal sınır)

Repo: `/tmp/niyetsen-research/rea` (morluto/rea, MIT, `rea-agents` 6.5.0,
Node ≥22.19). Yerel çalışır; MCP kurulumu (`npx rea-agents setup`) **Şahin
onayı** ile yapılır (MCP governance).

İzinli kullanım: kendi APK/AAB'mizi (`niyetsen-v9-play-internal.aab`) analiz
etmek (izin/manifest denetimi, Flutter/RN tespiti, gömülü string sızıntısı),
kendi web sitemizi `inspect_web_page` ile denetlemek, **herkese açık web
sayfalarının** DOM/SEO yapısını okumak.

Yapılmaz (REA DISCLAIMER + KVKK + telif): rakip APK'yı decompile edip kod/asset
kopyalamak, lisans/kimlik doğrulama atlatmak, rakip API'lerine yetkisiz trafik.
Rakip **özellik** öğrenimi yalnız herkese açık sayfa, mağaza listesi, demo
videosu ve kullanıcı yorumlarından yapılır.

## Araştırma yenileme adımları

1. `WebSearch` ile her sistem için "X HR dashboard features 2026" + fiyat.
2. Yeni bulguyu tabloya tarihle ekle; çelişen eski satırı "Eski" bölümüne taşı.
3. Gizlilik tabanını değiştiren bir bulgu varsa `docs/NIYETSEN_V2_KURUMSAL_PIVOT_MASTER_PLAN.md`
   §Gizlilik bölümünü de güncelle — iki yer çelişmez.
