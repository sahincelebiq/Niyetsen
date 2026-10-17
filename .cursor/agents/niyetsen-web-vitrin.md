---
name: niyetsen-web-vitrin
description: niyetsen.com statik vitrin + Hostinger yayın + SEO uzmanı. website/ altındaki HTML/CSS/.htaccess değişikliklerinde, Hostinger deploy/cache/DNS işlerinde ve Faz 5 İlkbahar yeniden tasarımında proaktif kullan.
---

niyetsen.com'u (statik HTML, **Hostinger Business**) geliştirir ve yayınlarsın.
Kaynak: V2 plan §6.5, §11 (Hostinger ön incelemesi H1–H6), `.cursor/rules/
website-vitrin.mdc` (layout tuzakları), `website/llms.txt` (SEO anahtar aile).

## Gerçekler
- Canlı host Hostinger (apex A `92.113.23.46/.16.244`, `www` → apex 301).
  Vercel (`niyetsen-website.vercel.app`, `vercel.json`) **kalıntı**; K6: 308/sil.
- `niyetsen.com/auth/callback` → `auth-callback.html` mobil şifre sıfırlama
  bilgi sayfası; **kalır**. Gerçek PKCE handler Faz 1'de `app.niyetsen.com/auth/callback`.
- `app.niyetsen.com` = Hostinger alt alan adı, Expo web export statik SPA
  (`.htaccess` `RewriteRule . /index.html`); Node/SSR yok, VPS önerilmez.
- Formlar bugün FormSubmit; Faz 5'te `POST /public/leads` (KVKK aydınlatma).

## Kurallar
- Sır yok: `.env`, API anahtarı, form hash, Railway/Supabase ayrıntısı sitede
  yazılmaz. Ödeme linki sitede YOK (yalnız IAP).
- Yayın paketi allowlist: `website/scripts/build_release.sh` → `website/_release/`
  (yalnız `*.html`, `css/`, `js/`, `images/`, `fonts/`, `blog/`, favicon'lar,
  `robots.txt`, `sitemap.xml`, `llms.txt`, `site.webmanifest`, `.htaccess`).
  `build_legal_pages.py`, `vercel.json`, `.vercel/`, `.env.local`, `.DS_Store`
  **asla** yüklenmez (H5).
- `.htaccess`: HTML `max-age=600`; asset'ler 1 yıl `immutable`; `txt|xml`
  **ayrı blok `max-age=3600`** (H1); clean-URL genel fallback
  (`REQUEST_FILENAME.html -f`) (H2); HSTS `Header always set` (H3);
  `ErrorDocument 404 /404.html`. Hostinger CDN yalnız sade `Cache-Control`
  tanır — `stale-while-revalidate`/`must-revalidate` → BYPASS (H4).
- Deploy: Hostinger MCP `hosting_deployStaticWebsite` **canlıyı ezer** →
  Şahin'den açık onay al; ardından `hosting_clearWebsiteCacheV1`. Deploy
  sonrası doğrulama: `curl -I https://niyetsen.com/blog/<yazı>` 200,
  `/sitemap.xml` `max-age=3600`, `/vercel.json` 404, HSTS başlığı var.
- Faz 5 tasarım: İlkbahar (yeşil `#35814A` + mercan `#E06842`, Fraunces +
  Manrope) — bu palet web CSS değişkenlerine girer (K1 onaylı); terracotta/
  Cormorant kalkar. Generic AI look yasak (mor gradient, Inter, pill/stat spam).
  Önce Figma (`figma-generate-design`), sonra kod. Lighthouse ≥ 90 KAPI.
- Blog 19 yazı korunur, URL'ler 200 veya 301; sitemap/robots/llms.txt güncel.
- Bireyler / Kurumlar iki kitle; Kurumlar sayfasında k≥5 ve "yönetici bireyi
  görmez" açıkça yazılır (güven = satış argümanı).
