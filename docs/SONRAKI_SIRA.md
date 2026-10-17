# Sonraki sıra — V2 Kurumsal Pivot kuyruğu (kilit, 2026-10-17 — Şahin)

> Şahin 17 Eki: "Faz 0'a başlayabilirsin." Tek kaynak:
> `docs/NIYETSEN_V2_KURUMSAL_PIVOT_MASTER_PLAN.md` §13 (KAPI'lı faz planı).
> Kural: **KAPI geçmeden sonraki faza başlanmaz.** Play Store sprinti
> (IAP + Data Safety) bu kuyrukla **paralel** sürer; aşağıdaki "Paralel ray"
> bölümü onun operasyon notlarıdır.

## V2 faz sırası

| Faz | Konu | Süre | KAPI | Durum |
|---|---|---|---|---|
| **0** | Hazırlık ve zemin: plan onayı işlemleri, README V2, Supabase panel (leaked-password, Google/Apple, redirect), migration tek kaynak + `SUPABASE_BAGIMLILIK.md`, günlük `pg_dump` + `verify_backup.py` + restore tatbikatı, 4 alt ajan + hook'lar, AAB güvenlik taraması, `mobile/AGENTS.md` v54, Hostinger P1 (H1–H6) | 2–3 gün | Restore tatbikatı yeşil (satır + md5); Google web girişi etkin; README V2 yayında; pytest 381 / tsc 0 | **AKTİF** (2026-10-17) |
| 1 | Kimlik, anket, çok model, web uygulaması: router bölme → model router (2.5 çıkar, `/health` sadeleşir, `model_usage_log`) → Vision fixture (B4 kapanır) → Argon A/B → `user_surveys` + 3 ekran → iki sekmeli giriş → `app.niyetsen.com` Expo web export → `api.ts` bölme, 7 hex → token, `AUTH_DISABLED` varsayılan false → **AAB kapanışı** (R23: `RECORD_AUDIO` blockedPermissions, implicit token dalı kaldır + `state`, R8 açık) → `image_url` göreli anahtar (R21) | 1–1.5 hafta | Web'de Google ile giriş + aynı hesap mobilde; anket cihazda; router birim testleri; Vision fixture yeşil; yeni AAB YÜKSEK 0; tsc 0; pytest ≥ 420 | bekliyor |
| 2 | Organizasyon çekirdeği: V2 §5.3 tabloları (migration), `org_service` + `/org/*`, `core/authz.py`, `wallet_service` + `outbox_service` (bayrak kapalı), mobil `davet.tsx` / `kurumum.tsx`, Rapor "Kurumum" kartı | 1.5–2 hafta | Davet → onay → kurumsal niyete plan bağlama uçtan uca; `test_privacy_k5.py` iskeleti; scoring testleri aynı | bekliyor |
| 3 | İK paneli + rollup + içgörü: `org_daily_rollups` cron, k≥5 guard, `(org)/` ekranları, `react-native-svg` grafikler, CSV (audit), PostHog org event'leri | 2 hafta | 2 pilot kurum; k<5 gizleniyor; panel taşmasız; **Expo vs Next.js kararı** | bekliyor |
| 4 | Platform admin + maliyet görünürlüğü | 3–4 gün | Admin dışı `/admin` 403; model maliyeti günlük görünür | bekliyor |
| 5 | niyetsen.com yenileme (İlkbahar) + Hostinger yayın + `/public/leads` | 1 hafta | Lighthouse ≥ 90; eski URL'ler 200/301; formlar API'ye | bekliyor |
| 6 | Kurumsal faturalama (RC Web Billing / fatura) + RC deney #1 | 1 hafta | Koltuk aktif → PRO; iptal → 24 sa içinde kalkar | bekliyor |
| 7 | Büyük sunucuya geçiş (V2 §7.2) | 1 hafta + 14 gün | Satır/md5/puan toplamı eşit; 24 sa hata < %1; geri dönüş test edildi | bekliyor |
| 8 | Ödül/entegrasyon pazarı (partner, kupon, "Ödüller") | sonra | Sandbox partnerde kupon uçtan uca; harcama rank düşürmez | bekliyor |

## FAZ 0 — açık/kapalı (canlı liste)

Kutucukların tek gerçek kaynağı V2 plan §13 FAZ 0 bloğudur; burada yalnız
**kimde** olduğu yazar.

| Madde | Kim | Not |
|---|---|---|
| Plan onayı işlemleri (MASTER_PLAN §1.14, SONRAKI_SIRA, hafıza sözlüğü) | ben | ✅ 2026-10-17 |
| README V2 + README_BACKEND | ben | ✅ 2026-10-17 (eski README arşivde) |
| Migration tek kaynak + `docs/SUPABASE_BAGIMLILIK.md` | ben | ✅ kök kopya kaldırıldı; envanter yazıldı |
| Günlük `pg_dump` cron + `scripts/verify_backup.py` + `docs/GECIS_PROTOKOLU.md` | ben | ✅ kod + cron adımı + `Dockerfile.cron` + 21 test; stand-in tatbikat EŞİT |
| **Restore tatbikatı — üretim** (KAPI 0) | **sen** → ben | `.env` `DIRECT_URL` şifresi (`[YOUR-PASSWORD]` duruyor) + Railway `cron` env'ine `BACKUP_*` + S3 kova kimliği (öneri: Cloudflare R2) → `scripts/restore_drill_local.sh --from-source` |
| 4 alt ajan + hook'lar | ben | ✅ `.cursor/agents/`, `.cursor/hooks.json` (canlıda doğrulandı) |
| AAB güvenlik taraması → `docs/security/AAB_TARAMA_2026-10.md` | ben | ✅ KRİTİK 0 · YÜKSEK 2 (RECORD_AUDIO, deep-link token) → F1 AAB'sinde kapanır |
| `mobile/AGENTS.md` v54 | ben | ✅ |
| Hostinger `.htaccess` H1–H3 + P2 + `404.html`, yayın allowlist, canlı deploy | ben | ✅ 2026-10-17 yayında doğrulandı (blog 200, sitemap 1 saat, HSTS, `vercel.json` 404) |
| Cron yeniden deploy (`Dockerfile.cron`) | ben (sen "deploy et" deyince) | `niyetsen-backend/` içinden `railway up --service cron --ci`; env'ler girilmeden de zararsız (`not_configured`) |
| Hostinger CDN BYPASS (H4) | **sen** | API: önbelleksiz mod kapalı + site önbelleği açık; canlıda HTML ve CSS hâlâ `x-hcdn-cache-status: BYPASS`. hPanel → Performans → CDN |
| Vercel kalıntısı: `niyetsen-website.vercel.app` 308 → niyetsen.com veya projeyi sil (H6/K6) | **sen** | Vercel'i GitHub'a bağlamak **gerekmez** — site Hostinger'da |
| Supabase: leaked-password koruması **aç** (R3) | **sen** | Authentication → Attack Protection |
| Supabase: Google + Apple sağlayıcı **etkin** (R4) | **sen** | Authentication → Sign In / Providers; Google client ID/secret, Apple Services ID |
| Supabase: redirect URL'leri (`https://app.niyetsen.com/auth/callback`, `https://panel.niyetsen.com/auth/callback`, `niyetsen://auth/callback`) | **sen** | Authentication → URL Configuration; `https://niyetsen.com/**` jokerini kesin yollara çevir |

## Paralel ray — Play Store / RevenueCat (operasyon notları, 2026-08-16'dan)

Play Console **Kapalı test — Alpha `10 (1.0.1)`**. RevenueCat JSON yüklü;
**Credentials need attention** Google gecikmesi (dakika–24 saat). Play daveti
Active. Fiyat kilit: aylık **150 TL**; yıllık fallback **1.200 TL** (150×8).

### Dahili test ≠ Kapalı test (Alpha)

Play'de bunlar **ayrı ray**. Biri dolunca diğeri güncellenmez.

| Ray | Menü | Kim görür | 1.0.1 (v10) |
|-----|------|-----------|-------------|
| **Dahili test** | Test edin ve yayınlayın → Test → **Dahili test** | Yalnız dahili liste + o rayın opt-in linki | Hâlâ **5 Ağustos** yazıyorsa bu raya v10 **yüklenmemiş** demektir. Normal. |
| **Kapalı test (Alpha)** | Test edin ve yayınlayın → Test → **Kapalı test** | Kapalı test e-posta listesi + Alpha opt-in | Ekrandaki inceleme **burası**. |

Aynı AAB iki raya da yüklenebilir; versionCode 10 her ikisinde de geçerli.
**Yönetilen yayınlama:** kontrol bitince Yayın özeti → değişiklikleri
**yayınla**; tester güncellemeyi 1–2 saatte çeker.

### RevenueCat — tıklama yolu

Kod + RC iskelet hazır: Play app `com.niyetsenai`, entitlement `premium`,
offering `default`. Ürünler: `niyetsen_monthly:monthly` (P1M),
`niyetsen_yearly:yearly` (P1Y) — V2 plan §2'ye göre RC'de **aktif**.

1. Play Console → Google Play ile para kazanın → Ürünler → Abonelikler:
   `niyetsen_monthly` / temel plan `monthly` (150 TL); `niyetsen_yearly` /
   `yearly` (fiyat Şahin). Ayarlar → Lisans testi: sen + Busra + kapalı test
   e-postaları. Abonelikler **aktif** olmalı.
2. RevenueCat → proje Niyetsen → Apps → Niyetsen Play (`com.niyetsenai`) →
   Play service account JSON → Products (`niyetsen_monthly:monthly`,
   `niyetsen_yearly:yearly`) → Entitlements → premium → Offerings → default
   (`$rc_monthly`, `$rc_annual`) → Integrations → Webhooks:
   `https://api-production-86f1.up.railway.app/webhooks/revenuecat`,
   `Authorization: Bearer <Railway REVENUECAT_WEBHOOK_SECRET>`.
3. RC Experiment #1 (yıllık vurgulu vs aylık vurgulu paywall) → **Faz 6**,
   Play ürünü canlı olunca.

### Eski kuyruk (2026-08-16) → V2'de nereye gitti

| Eski madde | V2 karşılığı |
|---|---|
| Ödeme UI (İlkbahar paywall) | yapıldı; mağaza fiyatı RC yeşillenince |
| Raporlar (panel + 1 cümle ayna, kural bazlı) | korunur; "Kurumum" kartı Faz 2 |
| Mistik akışlar | Play sprinti içinde sürer; org'a veri akmaz (kilit) |
| Ana sohbet ajanı | Faz 1 model router üstüne; araç listesi `core/tools.py` |
| Örüntüleme (ConvNet yok) | Faz 3 kural bazlı içgörü + bireysel ayna |
| MiniMax-M3 aday | **kapandı** — çok modelli Gemini (V2 §5.5) |
| Public leaderboard | v3 — hâlâ yok; org içi opt-in lig Faz 3 "Challenge (v2.1)" |
