# Niyetsen — İş Planı & Fizibilite (v2 — Gerçek İlerleme Güncellemesi)

> **v2 notu (2026-07-12):** Bu belge, 2026-06-28 tarihli v1 fizibilite belgesinin
> güncellemesidir. v1, geliştirme başlamadan ÖNCE yazılmış saf projeksiyondu.
> Bu v2, §6.3 ve §10'da **gerçek geliştirme ilerlemesini** (git commit geçmişi +
> bağımsız kod doğrulaması + otomatik test sonuçları + Şahin'in gerçek cihaz
> testi) ekliyor. Geri kalan bölümler (pazar araştırması, senaryolar, birim
> ekonomisi) henüz gerçek kullanıcı verisi gelmediği için v1'den değişmeden
> aktarıldı — bunlar hâlâ projeksiyondur, gerçek değil.
>
> Eşlik edenler: uygulama-promt.md, 01-mvp-plan.md, 02-mimari.md, 03-algoritma.md,
> NIYETSEN_MASTER_PLAN.md (aktif faz durumu — tek gerçek kaynak).
> Kur referansı: 1 USD ≈ 46,6 TL (Haziran 2026). Maliyetler dolar bazlı, fiyatlandırma TL.

---

## 1. Yönetici Özeti

Niyetsen, kullanıcının "bu yıl nasıl bir hayat istiyorum" niyetini sohbet üzerinden alıp görselli, günlük, oyunlaştırılmış bir yıllık plana çeviren bir kişisel yaşam asistanıdır. Gemini destekli AI bir plan üretir, kullanıcıyı görevleri fiilen yapmaya (gidip fotoğraf çekme, alarm/takvim) yönlendirir, yapmadığında puan kaybettirir. Üzerine Türkiye'nin kültürel olarak güçlü olduğu fal/astroloji modülü (kahve falı, el falı, tarot, burç) günlük tekrar tüketim ve duygusal bağ yaratır.

İş modeli: ücretsiz deneme (ilk gerçek plan + birkaç gün görev denemesi ücretsiz) → ardından aylık 450 TL abonelik. Geliştirme bizzat vibe-coding ile (Cursor + Claude Code, Python/FastAPI backend + Expo mobil), bu da geliştirme maliyetini bir geliştirici ekibinin onda birine indiriyor.

Tek satırlık tez: Düşük maliyetle inşa edilen, Türkiye'nin fal kültürüne + oyunlaştırma + kişiselleştirme retention çarpanlarına yaslanan, kanıtlanmış (ölçülmüş retention eğrisiyle) bir niş B2C abonelik ürünü.

**v2 eki:** Bu tez artık kısmen kanıtlı — ürünün çekirdek halkası (sohbet→plan→görev→foto kanıt→puan→rank→bildirim) 5 takvim gününde inşa edildi ve hem otomatik testlerle (86/86) hem gerçek cihazda elle doğrulandı (bkz. §10).

## 2. Ürün

Çekirdek halka: Sohbet → AI sorularla niyeti netleştirir → görselli yıllık plan → günlük görev + foto kanıtı → puan/rank → yapmazsa ceza + duygusal bildirim → tekrarlılık.

Kritik tasarım kararı — ücretsiz "aha" anı: kullanıcı ilk gerçek planını ücretsiz görür ve birkaç gün görevleri dener; ödeme duvarı ancak değer hissedildikten sonra gelir. Sebep: tüm denemelerin %80–90'ı ilk gün oluyor; kullanıcı "vay be" demeden 450 TL'yi gözden çıkarmaz. "Kaybetme korkusu" satışı, "tatmadan öde"den çok daha güçlü.

🖼️ [Onboarding akışı ekran görüntüleri — UI hazır olunca] 🖼️ [Örnek görselli plan ekranı — UI hazır olunca]

## 3. Pazar Araştırması

Genel uygulama gerçeği (2026 benchmark): Retention acımasız. Ortalama D1 tutma %25–30, D7 %10–15, D30 medyanı tüm kategorilerde ~%4. Productivity uygulamaları D30'da %2,8–4,1. Yani indirme sayısı yalandır; iş düşüş eğrisinde biter. (Kaynak: AppsFlyer State of App Marketing 2026, Statista, UXCam.)

Niyetsen'in lehine üç kuvvet:

- Türkiye + fal kültürel uyumu. Kahve falı Türkiye'deki en yaygın fal türü; Faladen gibi AI destekli kahve falı/tarot/astroloji uygulamaları zaten pazarda. Bu, günlük tekrar tüketim ve duygusal bağ demek.
- Oyunlaştırma çarpanı. Sektör verisi: puan/rozet/ilerleme mekanikleri günlük aktif kullanıcıyı ~2,6 katına çıkarıyor.
- Kişiselleştirme çarpanı. Birebir kişiselleştirme retention'ı ~%45'e kadar yükseltiyor. Niyetsen'in planı kişiye özel.

Global trend rüzgârı: Astroloji uygulama pazarı 2024'te ~3 milyar USD, 2030'a doğru ~9 milyar USD beklentisi (CAGR ~%20). Self-care + AI birleşimi büyüyen bir niş. Türkiye bu trendin kültürel olarak en hazır pazarlarından.

Rekabet: Saf fal uygulamaları (Faladen vb.) var ama "yaşam planlama + oyunlaştırma + fal"ı birleştiren yok. Niyetsen'in farkı kombinasyon: fal tek başına tüketim, plan+rank ise tutunma motoru.

## 4. Pazar Büyüklüğü (TAM / SAM / SOM)

Uyarı: Top-down TAM rakamları yatırımcının en az güvendiği sayılardır ("20 milyar pazarın %1'i" cümlesi uyutur). Aşağısı yön gösterir; asıl değer §7'deki bottom-up funnel'da.

- TAM (Türkiye): ~85M nüfus, ~70M+ akıllı telefon kullanıcısı. Self-gelişim + fal/astroloji ilgisi olan 18–45 yaş yetişkin ≈ 25–30M kişi.
- SAM: Bu kitleden bir yaşam/fal uygulamasıyla aktif etkileşime girip ödeme potansiyeli olanlar ≈ 4–7M kişi.
- SOM (ilk 12–24 ay, gerçekçi ulaşılabilir): İyi pazarlama + organik ile 50.000–200.000 indirme, bunun küçük bir yüzdesi ödeyen → birkaç bin aktif abone. Asıl hedef bu, milyonlar değil.

## 5. İş Modeli & Fiyatlandırma

- Ücretsiz deneme: ilk gerçek plan + birkaç gün görev + (sınırlı) günlük fal hakkı.
- Abonelik: 450 TL/ay → sınırsız sohbet, tam yıllık plan, hep hatırlama, oyunun tamamı, günlük fal hakları.
- Para birimi notu: 450 TL TR için yüksek bir eşik (asgari ücretin ~%1,6'sı/ay). İlk 7 gün tam erişimli deneme + yıllık plan indirimi (örn. 3.600 TL/yıl = aylık ~300 TL eşdeğeri) dönüşümü artırabilir. Test edilecek.

## 6. Maliyet & Fizibilite

### 6.1 Geliştirme aşaması — aylık tekrarlayan (gelir öncesi, v1 PROJEKSİYONU)

| Kalem | Plan | Aylık USD | Aylık TL (≈) |
|---|---|---|---|
| Cursor (evin) | Pro+ ($60) — ağır kullanım | 60 | 2.800 |
| Claude Code (dostun) | Pro ($20) ile başla; limite çarparsan Max 5x ($100) | 20–100 | 930–4.660 |
| Gemini API | Ücretsiz katman MVP'yi büyük ölçüde karşılar; aşınca 2.5 Flash $0,30/$2,50 per 1M | 0–15 | 0–700 |
| Backend hosting | Railway/Render başlangıç | 5–20 | 230–930 |
| Veritabanı | Supabase (ücretsiz → Pro $25) | 0–25 | 0–1.165 |
| Unsplash (görsel) | Ücretsiz | 0 | 0 |
| **Toplam (yalın)** | | **~45** | **~2.100** |
| **Toplam (orta)** | Cursor Pro+ + Claude Pro + Railway | **~85** | **~3.960** |
| **Toplam (ağır)** | Cursor Pro+ + Claude Max + Supabase Pro | **~205** | **~9.550** |

### 6.2 Tek seferlik / yıllık maliyetler (yayın için, v1 PROJEKSİYONU)

| Kalem | Maliyet | TL (≈) | Ne zaman |
|---|---|---|---|
| Apple Developer Program | $99/yıl | ~4.615/yıl | App Store yayını — henüz açılmadı |
| Google Play Developer | $25 tek sefer | ~1.165 | Play Store yayını — henüz açılmadı |
| Domain (ai.niyetsen.com) | Hostinger üzerinden alındı (2026-07) | ▢ gerçek tutar | Alındı |
| Hostinger hosting (vitrin sitesi) | Kuruluyor (2026-07) | ▢ gerçek tutar | Kuruluyor |
| RevenueCat | Aylık $2.500 gelire kadar ücretsiz | 0 | Abonelik gelince |
| **Toplam başlangıç (v1 tahmini)** | ~$136 | ~6.340 | |

### 6.3 GERÇEK HARCAMA — Şu Ana Kadar (2026-07-12 itibariyle) — YENİ

> Aşağıdaki kalemler henüz kesinleşmedi; ▢ işaretli yerler gerçek fatura/plan
> bilgisiyle doldurulmalı. Bu tabloyu doldurunca §6.1'deki v1 projeksiyonuyla
> karşılaştır — vibe-coding'in gerçek maliyeti tahminin altında mı üstünde mi
> çıktı, bu satır yatırımcı/kendi karar hikâyen için değerli.

| Kalem | Gerçek plan/tutar | Kaç gündür aktif |
|---|---|---|
| Cursor | ▢ | ▢ |
| Claude Code | ▢ | ▢ |
| Gemini API | ▢ (ücretsiz katman mı, faturalı mı) | ▢ |
| Supabase | ▢ (ücretsiz mi, Pro mu) | 2026-07-10'dan beri aktif kullanımda |
| Domain (ai.niyetsen.com) | ▢ | Satın alındı |
| Hostinger hosting | ▢ | Kurulum aşamasında |
| Apple/Google Developer hesapları | Henüz açılmadı | — |
| **Toplam gerçek harcama (5 gün)** | **▢** | |

**Geçen gerçek süre: 5 takvim günü** (ilk commit 2026-07-07 → bugün 2026-07-12). Bu sürede Faz 0, 1, 2 ve büyük ölçüde 3-4 tamamlandı (bkz. §10). v1'in "aylık yakım" tahminleri bu hıza göre yeniden okunmalı: eğer bu tempo sürerse yayın öncesi kalan işler (Faz 5-6) için gereken TAKVİM süresi v1'in "3-4 hafta" sezgisel varsayımından daha kısa olabilir — ama tek kişi + doğrulanmamış madde riski (§11'e eklenen yeni risk) bunu dengelemeli.

## 7. Üç Senaryo (Bottom-up Funnel) — v1 PROJEKSİYONU, değişmedi

Yatırımcının önemsediği kısım burası. Henüz gerçek kullanıcı verisi yok; aşağıdaki tablolar hâlâ varsayıma dayalı.

### 7.1 Pazarlama bütçesi → indirme

Varsayım: TR'de Meta/TikTok, iyi kreatif, fal/self-gelişim nişi için tahmini CPI (kurulum başı maliyet) 4–10 TL. Bu varsayımı önce küçük bir test bütçesiyle (örn. 3.000 TL) doğrula — funnel'ın en kırılgan girdisi.

| Aylık pazarlama | Kötü (CPI 10) | Orta (CPI 6) | İyi (CPI 4) |
|---|---|---|---|
| 20.000 TL | 2.000 indirme | 3.333 | 5.000 |
| 50.000 TL | 5.000 | 8.333 | 12.500 |

### 7.2 İndirme → ödeyen (her 5.000 indirme için)

| Metrik | Kötü | Orta | İyi |
|---|---|---|---|
| İndirme | 5.000 | 5.000 | 5.000 |
| D1 tutma | %22 → 1.100 | %28 → 1.400 | %35 → 1.750 |
| D7 tutma | %8 → 400 | %12 → 600 | %16 → 800 |
| D30 tutma | %4 → 200 | %7 → 350 | %11 → 550 |
| Duvarda satın alma | %1,5 → 75 | %3 → 150 | %5 → 250 |
| Aylık brüt gelir (×450 TL) | 33.750 TL | 67.500 TL | 112.500 TL |
| Store kesintisi sonrası net (~%70) | ~23.600 TL | ~47.250 TL | ~78.750 TL |

"İyi" senaryonun D30 %11 ve dönüşüm %5 olması, genel medyanın (D30 ~%4, freemium dönüşüm ~%2) üstünde — bunu mümkün kılan tek şey fal + oyunlaştırma + TR kültürel uyumu.

🖼️ [Funnel huni grafiği — sayılar gerçek kullanıcıdan gelince güncellenecek]

## 8. Birim Ekonomisi (LTV / CAC) — v1 PROJEKSİYONU, değişmedi

- Ödeyen başı net gelir (ARPU): 450 TL − store %30 ≈ 315 TL/ay net (ilk yıl; 2. yıldan sonra store %15'e düşer → ~382 TL).
- Abone ömrü (varsayım): Kötü 2 ay → LTV ≈ 630 TL. Orta 3 ay → LTV ≈ 945 TL. İyi 6 ay → LTV ≈ 1.890 TL.
- CAC: Orta 6 TL / %3 = 200 TL. Kötü 10 TL / %1,5 = 667 TL.
- LTV:CAC (sağlıklı eşik ≥ 3:1): Orta ~4,7:1 ✅. Kötü ~0,9:1 ❌. İyi ~14:1 🚀.

## 9. Başabaş (Break-even) — v1 PROJEKSİYONU, değişmedi

Aylık nakit yakımın (~4.000 TL orta kurulum) orta senaryoda 13–14 ödeyen aboneyle karşılanıyor.

## 10. Yol Haritası — GÜNCELLENDİ (gerçek durum, 2026-07-12)

| Faz | Durum | Tarih | Not |
|---|---|---|---|
| Faz 0 — Repo/İskelet | ✅ Tamamlandı | 2026-07-07 | |
| Faz 1 — MVP (sohbet→görselli plan) | ✅ KAPI 1 KAPANDI | 2026-07-07 | Uçtan uca gerçek Gemini ile doğrulandı |
| Faz 2 — Kalıcılık & Kimlik | ✅ Büyük ölçüde tamam | 2026-07-10 | Açık: Google/Apple OAuth sağlayıcı aktivasyonu (Supabase'de hâlâ external=false) |
| Faz 3 — Görev Motoru (kanıt+puan+zincir) | ✅ KAPI 3 fiilen kapandı | 2026-07-11/12 | 86/86 backend test + Şahin'in gerçek cihaz testi (foto→puan→rank). Açık: İrade Modu'nun otomatik tetikleme mantığı |
| Faz 4 — Bildirim + Rehber Kişiliği | ⚠️ Kod tamam, KAPI kısmen açık | 2026-07-11 | Kriz filtresi + scope guardrail test doğrulandı. Açık: bildirimin gerçek cihazda doğrulanması + "3 örnek diyalog" elle testi |
| Faz 5 — Paywall + Analitik + Uyum | ⬜ Başlamadı | — | RevenueCat, PostHog, gizlilik sayfaları |
| Faz 6 — Store Yayını | ⬜ Başlamadı | — | Apple/Google hesapları, EAS build, store varlıkları, TestFlight |
| Faz 7 — v2 (Fal modülü) | ⬜ Kapsam dışı | — | Retention verisi gelmeden başlanmayacak (kilitli karar) |

**5 günlük sprint sonucu:** Tek kişi + Cursor/Claude Code ile 5 takvim gününde
MVP + kalıcılık/kimlik + görev motoru + bildirim/rehber katmanı büyük ölçüde
inşa edildi ve büyük kısmı otomatik testle (86/86) + gerçek cihaz testiyle
doğrulandı. Bu hız v1'in "vibe-coding geliştirme maliyetini onda birine indirir"
tezini destekliyor. Ama iki yapısal risk var: (1) plan dosyası (checkbox) ile
git commit mesajları arasında senkron kopukluğu yaşandı — "tamamla" diyen
commit ile işaretlenmemiş checkbox aynı anda var olabiliyor, bu yüzden
ilerleme takibi düzenli bağımsız doğrulama gerektiriyor; (2) KAPI kriterlerinin
bir kısmı (elle cihaz testi, örnek diyalog) otomatik testle değiştirilemez —
kod yazılması "bitti" anlamına gelmiyor, KAPI'nin tamamı geçmeden sonraki faza
geçilmemeli (MASTER_PLAN §4 kuralı). Bir sonraki 30 günde gerçekçi hedef: Faz
2'nin açık maddesi (OAuth) + Faz 3-4'ün açık elle-doğrulama maddeleri kapatılıp
Faz 5-6'ya geçilmesi — bu hızla yayına 2-3 haftada ulaşmak imkânsız değil, ama
"KAPI atlama" riski gerçek ve MASTER_PLAN'ın en sert kuralı tam olarak bunu
önlemek için var.

## 11. Riskler & Azaltma

- 450 TL yüksek eşik (TR). → Ücretsiz "aha" anı + yıllık indirim + ilk 7 gün tam erişim testi.
- Retention medyanın altında kalabilir. → Fal+oyunlaştırma+kişiselleştirme kuvvetlerini ciddiye al; D7'yi erken ölç, kötüyse ürünü düzelt (pazarlamayı değil).
- Tek kişi bağımlılığı (sen). → Vibe-coding hız veriyor ama bitirme disiplini şart; haftalık rep takibi.
- AI maliyeti ölçekte artar. → Flash-Lite/Flash kademeli model, context caching (%90 tasarruf), sadece zor isteklerde Pro.
- Store reddi / politika. → Fal içeriğinde "eğlence amaçlıdır" ibaresi, abonelik kurallarına tam uyum.
- **YENİ (v2): Plan dosyası ↔ kod senkron kopukluğu.** Git commit mesajları
  "tamamla" derken plan dosyasındaki checkbox'lar işaretsiz kalabiliyor
  (Faz 3-4'te gözlemlendi). Azaltma: her fazın sonunda checkbox güncellemesi +
  bağımsız doğrulama commit'ten hemen sonra yapılmalı, "commit mesajı = bitti"
  varsayılmamalı.
- **YENİ (v2): KAPI kriterlerinin otomatik testle ikame edilememesi.** Bazı KAPI
  şartları (gerçek cihazda bildirim, örnek diyalog) doğası gereği elle
  doğrulama gerektiriyor; 86/86 otomatik test geçmesi bunları karşılamıyor.
  Azaltma: her KAPI'de "otomatik test" ve "elle doğrulama" ayrı satır olarak
  takip edilsin.

## 12. Yatırımcı İçin Asıl Mesele

Yatırımcı projeksiyon tablolarını dinlemez — hepsini şişirilmiş bilir. Bu belgedeki §7 senaryoları senin düşünmen için, yatırımcıya satış için değil. Yatırımcıyı uyandıran tek şey: gerçek retention eğrisi. "50 kişi indirdi, %X'i 7. günde aktif, %Y'si ödedi" — bu cümle 100.000 hayali kullanıcıdan değerlidir.

**v2 eki:** Bu belge artık ikinci bir gerçek veri türü de taşıyor — "5 günde
çekirdek ürün + 86 otomatik test + gerçek cihaz doğrulaması" hikâyesi. Bu,
retention verisinden önce gelen ama yine de gerçek bir kanıt: ekibin (tek kişi
+ AI ajanları) hız ve disiplin kombinasyonu çalışıyor. Yatırımcıya "ne kadar
hızlı inşa ettik" anlatmak, "kaç kişi indirdi"nin yerini tutmaz ama onu
bekleme sürecinde güven inşa eder.

🖼️ [Gerçek retention eğrisi grafiği — ilk kullanıcı kohortundan gelecek]
🖼️ [Faz ilerleme Gantt şeması — §10 tablosundan, tamamlanan/kısmi/planlanan renk kodlu]

---

*Bu belge bir yatırım tavsiyesi değildir; rakamlar benchmark ve varsayımlara dayalı projeksiyondur, garanti değildir (§1-9, §11). §6.3 ve §10'daki ilerleme verisi gerçektir (git commit geçmişi + kod okunarak + otomatik test çalıştırılarak bağımsız doğrulanmıştır, 2026-07-12). Finansal kararlar için kendi değerlendirmeni yap.*
