# Agent Handoff — Manus AI ↔ Cursor (ortak hafıza)

> **Amaç:** İki ajan birbirinin yaptığını kaybetmesin.  
> Manus bir şey yaptığında buraya yazar → Cursor okur. Cursor bir şey bitirdiğinde buraya yazar → Manus okur.

## Kurallar

1. Bu dosyayı **git'e commit et** (sırlar yazma).
2. Her giriş **en üste** ekle (yeniden eskiye).
3. Format sabit kalsın — parse etmesi kolay olsun.
4. Kod değişikliği varsa: **branch + commit hash** veya **PR linki** yaz.
5. `docs/FAZ5_AKTIF.md` ve `NIYETSEN_MASTER_PLAN.md` §1 kilitli kararları bozma.

---

## Şablon (kopyala-yapıştır)

```markdown
### [TARİH SAAT] — [Manus|Cursor] — [kısa başlık]

**Durum:** done | in_progress | blocked  
**Repo:** Niyetsen | Niyetsen-mobile | ikisi  
**Branch:** `branch-adı`  
**Commit/PR:** `abc1234` veya PR URL  

**Ne yapıldı:**
- madde 1
- madde 2

**Diğer ajana not:**
- Sonraki adım / dikkat / korunacak UX maddeleri

**Dosyalar:**
- `path/to/file.tsx`
```

---

## Aktif bağlam (sabit — sık güncelleme)

| Alan | Değer |
|------|-------|
| Aktif faz | FAZ 5 (mağaza bekliyor) |
| Mobil branch | `fix/ux-consent-optimizasyon` |
| Backend branch | `main` |
| Lokal API | `http://192.168.1.104:8000` |
| Prod API | `https://api-production-86f1.up.railway.app` |
| Supabase proje | `ktweahgrrppmxpdhohdh` |
| KAPI 3–4 | Kapalı — tekrar açma |
| Korunacak UX | `docs/FAZ5_AKTIF.md` §7 madde |

---

## Kayıt defteri (en yeni üstte)

### 2026-07-15 20:15 — Cursor — Backend push + Manus frontend handoff

**Durum:** done (backend) · in_progress (frontend Manus'ta)  
**Repo:** Niyetsen (backend) · Niyetsen-mobile (frontend yakında)  
**Branch:** `main`  
**Commit/PR:** `3b53fe1` — Nano Banana hibrit görseller  

**Ne yapıldı (Cursor):**
- Nano Banana (`gemini-2.5-flash-image`) + Unsplash hibrit plan görselleri
- `main` push: KAPI 3 QC, Railway MCP docs, cron araçları, Nano Banana
- gh CLI kuruldu + `sahincelebiq` auth; Railway api+cron Online
- Supabase migration bekliyor: `20260716000000_plan_images_bucket.sql`

**Diğer ajana not (Manus — frontend):**
- **Şimdi sen:** mobil/Expo frontend geliştirmesi (UI, ekranlar, UX)
- **Sonra Cursor:** diff incelemesi + backend entegrasyon kontrolü
- Korunacak UX (geri alma): `docs/FAZ5_AKTIF.md` §7 — KVKK `privacy`, tab bar tema, chat scroll, İrade Modu, paywall Alert
- Mobil branch: `fix/ux-consent-optimizasyon` (ayrı repo)
- Yeni plan görselleri: `image_source` = `unsplash` | `gemini_nano_banana` | `placeholder` — ⓘ atıf rozeti koru
- Lokal API: `EXPO_PUBLIC_API_URL=http://192.168.1.104:8000`

**Dosyalar (backend, main):**
- `niyetsen-backend/app/services/image_service.py`
- `niyetsen-backend/supabase/migrations/20260716000000_plan_images_bucket.sql`
- `docs/AGENT_HANDOFF.md`

---

### 2026-07-15 — Cursor — Manus MCP kuruldu

**Durum:** done  
**Repo:** Niyetsen  
**Branch:** `cursor/cron-railway-stability`  

**Ne yapıldı:**
- `.cursor/mcp.json` oluşturuldu (Manus MCP + Supabase MCP, gitignore'da)
- `docs/AGENT_HANDOFF.md` ve `docs/MANUS_CURSOR_SYNC.md` aktif

**Diğer ajana not (Manus):**
- Her oturum sonu bu dosyanın **en üstüne** özet ekle
- Instagram / store metinlerini buraya + ilgili `docs/` veya `mobile/` commit'e yaz
- Korunacak: KVKK `kvkk_explicit_consent` → `privacy`; mobil branch `fix/ux-consent-optimizasyon`

**Dosyalar:**
- `.cursor/mcp.json` (lokal, commit edilmez)
- `docs/AGENT_HANDOFF.md`

---

### 2026-07-15 — Cursor — Manus köprüsü kuruldu

**Durum:** done  
**Repo:** Niyetsen  
**Branch:** `cursor/cron-railway-stability`  

**Ne yapıldı:**
- `docs/AGENT_HANDOFF.md` ve `docs/MANUS_CURSOR_SYNC.md` oluşturuldu
- Manus MCP kurulum şablonu eklendi (API key kullanıcıda)

**Diğer ajana not:**
- Instagram Reels / store metinleri Manus'tan; kod/entegrasyon Cursor'dan
- KVKK: `kvkk_explicit_consent` → `privacy` (geri alma)
- Railway cron ops Fable 5'e ertelendi

**Dosyalar:**
- `docs/AGENT_HANDOFF.md`
- `docs/MANUS_CURSOR_SYNC.md`

---

_Eski kayıtlar aşağıya eklenir._
