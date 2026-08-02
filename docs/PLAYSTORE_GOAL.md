# /goal — Play Store çıkış + kusursuz ürün (2026-08-02)

> Şahin: sosyal medya dosyaları engel değil (yatırımcı ekip paylaşımı).  
> Bu dosya = aktif sprint hedefi. Her agent oturumu bunu + `FAZ8_LANSMAN.md` +
> `.cursor/rules/playstore-cikis-hafiza.mdc` okur.

## Tek cümle hedef

Niyetsen’i Play Internal testing’e **güvenli, kişiselleşmiş, eksiksiz arayüzlü**
çıkarmak: yatırımcı demo bug’ları kapanmış, sohbet **bağlam penceresi**
(sol niyet/sohbet paneli + sunucu KULLANICI BELLEĞİ) kusursuz, mistik/plan/profil
cilalı, kanıt semantik olarak sıkı.

## Yatırımcı bug’ları → durum → iş

| # | Demo bug (28 Tem) | İskelet | Kalan iş (bu goal) |
|---|-------------------|---------|---------------------|
| B1 | Sohbet yavaş / tekrar | RAG embedding kapalı, model 3.1 | Bellek bloğu zenginleştir; history tavanı; cihaz <8 sn smoke |
| B2 | Plan oluşturulamıyor | FORCE_PLAN + generate_batch | Cihaz smoke; hata UX sohbette net |
| B3 | Planlar arası geçiş | threads degrade + API sertifika | **Bağlam penceresi** UI kusursuz; cihaz 5× geçiş |
| B4 | Kanıt gevşek (su≠meyve) | Sıkı prompt | **8.6: GÖREV BAĞLAMI** (gün teması + plan adı + tiny) modele |
| B5 | Profil web gibi | Kısmen settings | Kompakt mobil hiyerarşi; burç/cinsiyet KAPI kapat |
| B6 | Cinsiyet yok | Backend+UI seçimi var | Onboarding atlanabilir soru + sohbet hitap smoke |
| B7 | Burç ikonu yok | zodiac.ts + mystic başlık | Profil + fal/tarot başlıklarında tutarlı glyph |
| B8 | Bildirimler yumuşak | emotional_penalty_body | Diğer reminder kopyaları aynı ton |
| B9 | Model zayıf | 3.1-pro-preview | Paid Gemini kota (Şahin Dashboard) |

## Geliştirme gereken yerler (öncelik)

### P0 — ürün adaleti + bağlam

1. **Kanıt kişisel bağlam (8.6)** — Vision’a: görev başlığı, tiny_version,
   gün teması, plan adı, kategoriler. Su ≠ meyve KAPI.
2. **Sohbet bağlam penceresi** — `ChatHistorySheet` / `ChatEdgeDrawer`:
   aktif sohbet+niyet net, boş/hata/yükleme durumları, soft dark uyumu,
   geçişte vision-board/sohbet karışmaz, erişilebilirlik.
3. **KULLANICI BELLEĞİ** — bugün görev *başlıkları*, aktif plan adı, niyet;
   boş alan gürültüsü yok (`prompt_builder`).

### P1 — eksik / cilasız arayüzler

4. **Profil (8.4)** — app hissi; cinsiyet 3 string; burç glyph+label.
5. **Plan düzenleme (8.3)** — Backend + mobil UI ✅; cihaz smoke Şahin.
6. **Mistik** — hub/tarot/fal/astroloji kart animasyonları; `MysticComingSoon`
   yalnız gerçekten kapalı özellikte; store’da fal ikincil.
7. **Rapor/Planım polish** — İlkbahar token, Reanimated only.

### P2 — lansman

8. Play IAP + Data Safety + targetSdk 36 + hesap silme URL.  
   Store görseller: `store-listing/` (Play 1080×1920 + iOS 1290×2796) ✅.
9. PostHog hunisi + Sentry 5xx/fallback.
10. Güvenlik raporundaki YÜKSEK’ler (EXIF, chat max_length, Redis limiter…) —
    ayrı onayla; bu goal’da ürün/UI önce, güvenlik düzeltmeleri sıralı.

### Bilinçli YOK (v3)

Public leaderboard, Pinterest, fine-tuning.

## Bağlam penceresi tanımı (kusursuz =)

| Katman | Dosya | Kusursuz kriter |
|--------|-------|-----------------|
| UI panel | `mobile/.../project-sheets.tsx`, `chat-edge-drawer.tsx` | Aktif thread/plan işaretli; yeni sohbet eskiyi silmez; 2. plan paywall doğru; dark/light; swipe+buton |
| Sunucu bellek | `prompt_builder.py` + `routes._task_memory` | İsim, burç, cinsiyet, niyet, plan adı, bugün görevleri, zincir/rütbe |
| Kanıt | `proof_service` + `PROOF_VALIDATION_PROMPT` | GÖREV BAĞLAMI dolu; anlamsal eşleşme |

## Çalışma protokolü

- Agent’lar paralel; commit yalnız Şahin isteyince (`faz8:` / `faz8-ui:`).
- mobil = ayrı repo `mobile/`.
- Reanimated: `Easing`/`Animated` asla `react-native`’den değil.
- Test: `pytest -q` yeşil; mobil `npx tsc --noEmit`.
- Kararsızlık: MASTER_PLAN §1 → hafıza → Şahin.

## Bu sprint çıkış KAPI’sı

- [ ] Su fotoğrafı meyve görevini geçemez (cihaz veya fixture).
- [x] Bağlam penceresi UI cilası (aktif rozet/rail, boş-hata, swipe+header) — cihaz 5× geçiş smoke Şahin.
- [x] Profilde cinsiyet+burç UI + onboarding atlanabilir cinsiyet (cihaz hitap smoke Şahin).
- [x] Mistik ana akışlar (astro/tarot/fal) shell+glyph; ComingSoon canlı rotada yok.
- [ ] Play Internal: Data Safety taslağı + AAB yolu net (form Şahin).
