# Yatırımcı Demo Günü — 28 Temmuz 2026

Son sistem denetimi: 27 Temmuz 2026. **Tüm kontroller yeşil.**

---

## 1. Sistem sağlık raporu (denetim sonucu)

| Kontrol | Sonuç |
|---|---|
| Backend otomatik test | **175 / 175 geçti** |
| Demo yolu testleri (sohbet, thread, persona, fal, görev döngüsü) | **55 / 55 geçti** |
| Mobil TypeScript (`tsc --noEmit`) | **0 hata** |
| Reanimated çökme koruması (lint kuralı) | **aktif ve doğrulandı** |
| Prod backend `/health` | **ok · env=prod · flash + pro modelleri** |
| API endpoint sayısı | **38** |
| Web sitesi (17 sayfa) | **0 kırık link**, sitemap 17 URL |
| Sır sızıntısı (git'te .env / token) | **yok** — hepsi ignore'da |
| `.env.example` içinde gerçek anahtar | **yok** |

---

## 2. Ürünün son hâli — ne var elimizde?

### Çekirdek (çalışıyor, demo edilebilir)
- **AI vizyon sohbeti** — kullanıcı belleği + RAG (felsefe, motivasyon, atomik
  alışkanlıklar, 16 senaryo) ile kişiye özel konuşma. Ücretsiz katmanda
  sınırsız. Sohbet oturumları başlıklarıyla saklanır, geçmişe dönülür.
- **Tek dokunuş hızlı yanıtlar** — model her soruyla birlikte 2-3 hazır cevap
  üretir; kullanıcı klavye açmadan onboarding'i bitirebilir.
- **365 günlük görselli plan** — kişinin şehrinden/zamanından türer; tempo
  kuralları: ilk günler garantili kazanım, haftada bir nefes günü, kademeli
  zorluk, görevlerin birbirine zincirlenmesi.
- **Fotoğraf kanıtı** — uygulama içi kamera + Vision değerlendirmesi, 3.
  denemede beyanla kabul; ceza tavanlı, puan tabanı sıfır.
- **Zincir & 6 kategori** — İrade, İstikrar, Disiplin, Özgüven, Sosyallik,
  Özsaygı; aylık zincir koruma jetonu.

### Ayrıştırıcılar (rakiplerde yok)
- **İdol Modu / Felsefe Yolları** — "onun gibi olmak istiyorum" anını 365
  günlük yola çevirir. Greenlights, Kaizen, Stoacı, Ustalık, Şafak yolları.
  Persona dossier altyapısı Supabase'de; **yeni idol eklemek deploy
  gerektirmez.** Hukuki çerçeve kodda zorlanır (felsefe adı + "ilham alır"
  notu; kişi adı pakette geçemez).
- **Mistik katman** — 78 kartlık tam tarot destesi + çekim animasyonu, kahve
  ve el falı görsel yorumu, günlük/haftalık burç, fal geçmişi. "Ayna, kader
  değil" ilkesi; her ekranda eğlence amaçlı ibaresi.

### Altyapı
- FastAPI + Supabase + Railway · Expo (iOS+Android tek kod tabanı)
- Gemini: sohbet/vision (Flash), plan (Pro), görsel (image), RAG embedding
- Store standardı güvenlik: gövde tavanı, güvenlik başlıkları, sızdırmayan
  hata yanıtları, timing-safe webhook, KVKK sürümlü rıza kaydı
- Cron dayanıklılığı: SIGTERM'de temiz çıkış, süre bütçesi, her hatada exit 0

---

## 3. Demo akışı (8-10 dakika, provası yapılmalı)

**Hazırlık (demodan 30 dk önce):**
1. `cd mobile && npx expo start -c` (temiz önbellek)
2. Telefonu uçak modundan çıkar, wifi'yi test et — **canlı API kullanılacak**
3. Uygulamayı bir kez baştan sona gez, ekranların yüklendiğini gör
4. Telefonu şarj et, rahatsız etme modunu aç, ekran parlaklığını yükselt

**Anlatım sırası:**
1. **Sorun (30 sn)** — "Kararların %92'si şubatta ölür. Sorun hedefte değil,
   hedefi güne çevirecek sistemde."
2. **Sohbet (2 dk)** — Yeni sohbet başlat, niyetini yaz, hızlı yanıt çipleriyle
   ilerle. *Vurgula:* rehber genel tavsiye vermiyor, kişiyi tanıyor.
3. **Plan (1,5 dk)** — Planı göster; kartların kademeli belirişi.
   *Vurgula:* görevler kişinin hayatından türüyor, şablon değil.
4. **Kanıt (1,5 dk)** — Bir görevi kamerayla tamamla, puanın işlenişini göster.
   *Vurgula:* "Söylemek değil, kanıtlamak. Bu mekanik kimsede yok."
5. **Zincir (1 dk)** — Rank ekranı, akan sayılar, kategori dağılımı.
6. **İdol Modu (2 dk)** — ☰ → Felsefe Yolları → Greenlights Yolu → sohbete
   aktar. *Vurgula:* "Bu özellik bir film izlerken doğdu; ilham anı 48 saatte
   söner, biz onu yakalıyoruz."
7. **Mistik (30 sn, opsiyonel)** — ☾ → günlük tarot. *Vurgula:* tutundurma
   kancası, ana konumlama değil.
8. **Kapanış** — README'deki üç katman + iş modeli + maliyet yapısı.

**Yedek plan:** İnternet giderse veya bir ekran takılırsa panik yok —
`docs/REKLAM_VIDEO_SENARYOLARI.md`'deki ekran kayıtlarını önceden al ve
telefonunda hazır tut. Canlı demo yerine kayıt göster, akış bozulmaz.

---

## 4. Yatırımcı sorularına hazır cevaplar

**"Teknik ekibin yok, tek kişisin — nasıl sürdüreceksin?"**
> Ürün AI-native geliştirme modeliyle inşa edildi: 175 otomatik test, merkezi
> tema katmanı, dokümante edilmiş mimari (MASTER_PLAN + faz dosyaları). Yeni
> özellik eklemek kod yazmayı gerektirmiyor bazı yerlerde — örneğin yeni idol
> eklemek sadece bir JSON dosyası.

**"AI maliyeti seni batırmaz mı?"**
> Kullanıcı başına aylık AI maliyeti ~0,1-0,2 USD; abonelik gelirinin %2'sinin
> altında. RAG embedding'leri disk önbelleğinde, plan üretimi partili, sohbet
> geçmişi 40 mesajla sınırlı — maliyet kontrolü mimaride.

**"Neden Habitica/Fabulous değil de bu?"**
> Habitica oyunlaştırır ama planı kişiselleştirmez; Fabulous rutin verir ama
> vizyon kurmaz; vision board uygulamaları "bakma" verir, "yapma" vermez.
> Niyetsen üçünü birleştiren tek ürün — üstüne kanıt mekaniği ve İdol Modu.

**"Fal kısmı ciddiyeti zedelemez mi?"**
> Konumlama net: yaşam planlama uygulaması. Mistik katman gizli bir bölümde,
> ikincil özellik olarak duruyor; App Store 4.3 riskini bu yüzden yönetiyoruz.
> Ama retention açısından güçlü bir günlük dönüş kancası.

**"Ne kadar süre sonra yayında?"**
> Kod tarafı hazır (Faz 7 kapalı). Kalan: mağaza hesapları, IAP ürünleri ve
> store inceleme süresi. Teknik borç yok, blokaj yok.

---

## 5. Demo sonrası ilk 3 iş (yol haritası)

1. **Mağaza yayını** — Apple/Google developer hesapları, IAP ürünleri, EAS
   production build, store varlıkları (`STORE_READINESS.md`).
2. **İlk 50 kullanıcı + D1/D7 retention ölçümü** — PostHog kurulu, event'ler
   bağlı; yatırımcı hikâyesinin gerçek verisi burada oluşur.
3. **İdol Modu genişletme** — 10 persona dossier'ı (Cursor promptu hazır),
   kategori filtresi, Gemini Search grounding ile doğruluk katmanı.

---

## 6. Bilinen sınırlar (dürüst liste — sorulursa)

- Mağaza IAP uçtan uca sandbox testi henüz yapılmadı (hesaplar bekleniyor).
- Supabase free katmanda; lansman haftasında Pro'ya geçilecek (yedekleme ve
  inaktivite duraklatması nedeniyle).
- Küçük Arkana kart görselleri henüz yok (metin yorumları tam).
- İdol Modu şu an 1 tam dossier + 5 markdown yol ile çalışıyor; 10 persona
  içerik üretimi sırada.
